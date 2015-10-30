import os, sys
import shutil
import random
import requests
import httplib2
import json
from helpers import *
from datetime import timedelta
from flask import Flask, render_template, request, redirect, abort
from flask import jsonify, url_for, flash, make_response, Markup
from flask import session as login_session, send_from_directory
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from werkzeug import secure_filename
from models import Base, User, Category, Item



# Default image for items obtained here
# http://www.clker.com/cliparts/q/L/P/Y/t/6/no-image-available-hi.png

APPLICATION_NAME = "Imperial Catalog"

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])

engine = create_engine("sqlite:///catalog.db")
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.jinja_env.globals['logged_on'] = logged_on

#app.permanent_session_lifetime = timedelta(minutes=10)



# From http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
def allowed_file(filename):
    '''
        def allowed_file(filename):

            Checks the filename to see if it has an allowed extension

            The filename is checked for a '.' and everything to the left
            of the '.' is checked against the ALLOWED_EXTENSIONS list.

            The both are true, the file is an 'allowed file'.
    '''
    return '.' in filename and \
           (filename.rsplit('.', 1)[1]).lower() in ALLOWED_EXTENSIONS


#  Taken from http://flask.pocoo.org/snippets/3/


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = login_session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

def generate_csrf_token():
    if '_csrf_token' not in login_session:
        login_session['_csrf_token'] = random_string()
    return login_session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


# Create anti-forgery state token
@app.route('/login')
def showLogin():

    return render_template('login.html')


@app.route('/ajax/gconnect', methods=['POST'])
def gconnect():

    # Obtain authorization code
    code = request.form.get('code')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    print access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()

    login_session['name'] = data['name']
    login_session['image'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])

    if user_id is None:
        user_id = createUser(login_session)

    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['name']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['image']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['name'])
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/ajax/gdisconnect', methods=['POST'])
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['name']
        del login_session['email']
        del login_session['image']

        response = make_response(json.dumps(result))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps(result))
        response.headers['Content-Type'] = 'application/json'
        return response


def createUser(login_session):
    newUser = User(name=login_session['name'], email=login_session[
                   'email'], image=login_session['image'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None



'''
    def catalog(category=None):
    The catalog home page and the category pages
'''
@app.route("/")
@app.route("/catalog")
@app.route("/catalog/category/<category>")
def catalog(category=None):

    ''' If a category name was passed in,
        query the db for a category with a matching name
        and get all the items for that category.

        Otherwise, set items to the 10 newest items across
        all categories

    '''
    #login_session.permanent = True

    categories = getAllCategories()
    if category:
        category = session.query(Category).filter(Category.name == category).one()
        items = category.items
    else:
        items = getLatestItems(10)

    return render_template('catalog.html', categories=categories,
                               items=items, category=category)



''' def showItem(category_name=None, item_name=None):
    Function for showing specific items
'''
@app.route("/catalog/category/<category_name>/<item_name>")
def showItem(category_name=None, item_name=None):


    ''' Get the category_id from the name passed in.
        Then get the item from the category_id and
        the item name
    '''



    category_id = (session.query(Category)
                    .filter(Category.name == category_name).one()).id
    item = session.query(Item).filter(Item.category_id == category_id)\
        .filter(Item.name == item_name).one()


    if login_session['email'] == item.user.email:
        return render_template('item.html', item=item)

    return render_template('p_item.html', item=item)


''' Function for adding an item to the db '''
@app.route("/catalog/additem", methods=['GET', 'POST'])
@app.route("/catalog/<category>/additem", methods=['GET', 'POST'])
def addItem(category=None):

    ''' Set error to None.  Error will be used for checking
        the status of operations and displaying error
        information
    '''


    if 'email' not in login_session:
        return redirect(url_for("catalog"))



    error = None
    user_id = getUserID(login_session['email'])
    ''' If the url had a value for category get the category '''
    if category:
        category = session.query(Category).filter(Category.name ==  category).one()

    ''' Set categories to all categories'''
    categories = getAllCategories()


    if request.method == 'POST':

        ''' Get the values from the form '''
        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        ''' Check if the item name exists in the category '''
        if item_name_used(category_id, name):
            ''' Set the error statement '''
            error = "%s exists in the selected category. Pick a different name" % name
        else:
            ''' If the name doesn't exist add the item '''
            item = Item(name=name,description=description,category_id=category_id,user_id=user_id)

            session.add(item)
            session.commit()
            print  item.name, item.category.name
            ''' Check if the form had a file '''
            if request.files['image']:
                ''' Set file to the upload file'''
                file = request.files['image']

                ''' Set success and error to the results of addItemFileFolder '''
                success, error = addItemFileFolder(file, item.category_id, item.id)

                ''' If it was successful, set item.image to the filename and
                    add the item to the db again to update it
                '''
                if success:
                    item.image = file.filename
                    session.add(item)
                    session.commit()
        ''' If there was an error return to add item page with the error, '''
        if error:
            return render_template('add_item.html', categories=categories, error=error)

        else:
            ''' otherwise flash that the item wa added and go the show item page
                with the new item's info
            '''
            flash('Added %s!' % item.name)
            return redirect(url_for('showItem', category_name=item.category.name, item_name=item.name))

    else:
        return render_template('add_item.html', categories=categories, category=category)


''' Function for updating an item in the db '''
@app.route("/catalog/category/<category_name>/<item_name>/update", methods=['GET', 'POST'])
def updateItem(category_name, item_name):

    ''' Set error to None.  Error will be used for checking
        the status of operations and displaying error
        information
    '''
    if 'email' not in login_session:
        return redirect(url_for("catalog"))



    error = None

    category = session.query(Category).filter(Category.name == category_name).one()

    ''' Look for the item in the db, if it's not there set
        item to none and set the error message
    '''
    try:
        item = session.query(Item).filter(Item.category_id == category.id).filter(Item.name == item_name).one()
    except NoResultFound:
        item = None
        error = "No item exists with this name and category"


    if login_session["email"] != item.user.email:

        return redirect(url_for("catalog"))


    ''' Set categories to all categories'''
    categories = getAllCategories()

    if request.method == 'POST' and item is not None:
        ''' Get the values from the form '''
        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        ''' Check if the item name exists in the category
            and that it's not the name of the item being update.
            Set the error message if the name is a duplicate
        '''
        if item_name_used(category_id, name) and name != item.name:
            error = "%s exists in the selected category. Pick a different name" % name
        else:
            ''' Otherwise update the values of the item '''
            item.name = name
            item.description = description
            old_category_id = item.category_id
            item.category_id = category_id

            ''' Check if the form had a file '''
            if request.files['image']:
                ''' Set file to the upload file'''
                file = request.files['image']

                ''' If the name of the new image is the
                    same as the current image
                    Prefix the new image filename with
                    'copy_of_'.

                    Without this step, the new file name
                    would be deleted when cleanup occurs
                    to remove the old file since it had the
                    same name as the existing image.
                '''
                if item.image and item.image == file.filename:
                    file.filename  = "copy_of_" + file.filename

                ''' Set success and error to the results of addItemFileFolder '''
                success, error = addItemFileFolder(file, category_id, item.id)

                ''' If it was successful:
                        1. Checks if item.image has a value. If it does
                        try removing the old file.

                        2. Then if item.image has a value and the category_id
                        of the item is different than the category_id prior to
                        the update and file removal was successful, try removing
                        the folder for the item's image.

                        3.  If that was successful set item.image to the new filename
                '''

                if success:
                    if item.image:
                        success, error = removeOldFile(old_category_id, item.id, item.image)
                    elif item.image and category_id != old_category_id and success:
                        success, error = deleteItemFileFolder(old_category_id, item.id)
                    if success:
                        item.image = file.filename

            elif item.image and category_id != old_category_id:
                ''' if the item had an image and the category changed
                    move the item folder under the new category folder
                '''
                old_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/" % (old_category_id, item.id)
                new_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/" % (category_id, item.id)
                try:
                    shutil.move(old_folder, new_folder)
                except OSError:
                    error = "Error moving file folder"

            ''' Now the item changes can be commited to the db '''
            session.add(item)
            session.commit()

        ''' If there were errors return to the update page with the errors'''
        if error:
            return render_template('update_item.html', categories=categories, item=item, error=error)
        else:
            ''' Otherwise, go the the show item page with the updated item '''
            flash('Updated %s!' % item.name)
            return redirect(url_for('showItem', category_name=item.category.name, item_name=item.name))

    return render_template('update_item.html', categories=categories, item=item)


@app.route("/catalog/category/<category_name>/<item_name>/delete", methods=['GET', 'POST'])
def deleteItem(category_name, item_name):

    error = None

    if "email"  not in login_session:
        return redirect(url_for("catalog"))

    category = session.query(Category).filter(Category.name == category_name).one()

    try:
        item = session.query(Item).filter(Item.category_id == category.id).filter(Item.name == item_name).one()
    except NoResultFound:
        item = None
        error = "No item exists with this name and category"

    categories = session.query(Category).all()

    if request.method == 'POST' and item is not None:

        if login_session["email"] != item.user.email:
            return redirect(url_for("showItem", category_name=category_name, item_name=item_name))



        if item.image:
            success, error = deleteItemFileFolder(item.category.id, item.id)

            if success:
                item.image = None
            else:
                return redirect(url_for('showItem', category_name=item.category.name, item_name=item.name, error=error))

        category = item.category.name
        deleted_name = item.name
        session.delete(item)
        session.commit()
        flash("%s deleted!" % deleted_name)
        return redirect(url_for('catalog', category=category))
    else:
        return redirect(url_for('showItem', category_name=item.category.name, item_name=item.name, error=error))


@app.route('/uploads/<category_id>/<item_id>/<filename>')
def uploaded_file(category_id,item_id,filename):

    item_folder = "/%s/%s/" % (category_id, item_id)
    folder = app.config['UPLOAD_FOLDER'] + item_folder

    return send_from_directory(folder,
                               filename)

def item_name_used(category_id, name):
    try:
        item = session.query(Item).filter(Item.category_id == category_id).filter(Item.name == name).one()
        return True
    except NoResultFound:
        return False


def removeOldFile(category_id, item_id, filename):

    success = False
    error = None

    item_folder = "/%s/%s/" % (category_id, item_id)
    folder = app.config['UPLOAD_FOLDER'] + item_folder
    file_path = folder + filename
    try:
        os.remove(file_path)
        success = True
    except OSError:
        error = "Error on file deletion"

    return success, None


def addItemFileFolder(file, category_id, item_id):

    success = False
    error = None

    if allowed_file(file.filename):

        item_folder = "/%s/%s/" % (category_id, item_id)
        folder = app.config['UPLOAD_FOLDER'] + item_folder
        print item_folder, folder, file
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except OSError:
                error = "Error on creating file folder"
                return success, error

        try:
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))
            print file
        except:
            error = "Error on saving file"
            return success, error

        success = True
    else:
        error = "The filetype is not allowed."

    return success, error





def deleteItemFileFolder(category_id, item_id):

    success = False
    error = None

    try:
        item_folder = "/%s/%s/" % (category_id, item_id)
        folder = app.config['UPLOAD_FOLDER'] + item_folder
        shutil.rmtree(folder)
        success = True
    except OSError:
        error = "Error removing folder"

    return success, error


def getAllCategories():
    return session.query(Category).all()


def getLatestItems(num):
    return session.query(Item).order_by(Item.created.desc())[:num]




if __name__ == '__main__':
    app.secret_key = random_string()

    app.debug = True
    app.run(host='0.0.0.0', port=8000)
