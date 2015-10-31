'''  - Imperial Catalog -

       Sean Fallmann 10/30/2015

       A website with a Star Wars Galactic Empire Theme.
       Allows for users to authenticate via Facebook and
       Google.  Allows for all CRUD operations within the
       catalog.

       Update and Delete are relegated to the creator of
       the item.  Create is only allowed by authenticated
       users.
'''

import os
import sys
import shutil
import random
import string
import requests
import httplib2
import json
import datetime
from datetime import timedelta
from flask import Flask, render_template, request, redirect, abort
from flask import jsonify, url_for, flash, make_response, Markup
from flask import session as login_session, send_from_directory
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm.exc import NoResultFound
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from werkzeug import secure_filename
from werkzeug.contrib.atom import AtomFeed
from models import Base, User, Category, Item
from database import db_session as session


# Default image for items obtained here:
# http://www.clker.com/cliparts/q/L/P/Y/t/6/no-image-available-hi.png

APPLICATION_NAME = "Imperial Catalog"

# Client secrets file for Google authentication
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Name of the upload folder
UPLOAD_FOLDER = 'uploads/'

# Filetypes allowed for upload
# TODO: Verify by MIME type
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def logged_on():
    if 'email' in login_session:
        return True
    else:
        return False


app.jinja_env.globals['logged_on'] = logged_on


def random_string():
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for x in xrange(32))


# From http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
def allowed_file(filename):

    ''' Checks the filename to see if it has an allowed extension.

        The filename is checked for a '.' and everything to the left
        of the '.' is checked against the ALLOWED_EXTENSIONS list.

        If both are true, the file is an 'allowed file'.
    '''
    return '.' in filename and \
           (filename.rsplit('.', 1)[1]).lower() in ALLOWED_EXTENSIONS


@app.teardown_appcontext
def shutdown_session(exception=None):

    ''' Automatically removes database sessions at the end
        of the request or when the application shuts down.
    '''
    session.remove()


@app.before_request
def csrf_protect():

    ''' CRSF Token snippet from http://flask.pocoo.org/snippets/3/ '''

    login_session.permanent = True
    if request.method == "POST":
        token = login_session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)


def generate_csrf_token():

    ''' CRSF Token snippet from http://flask.pocoo.org/snippets/3/ '''

    if '_csrf_token' not in login_session:
        login_session['_csrf_token'] = random_string()
    return login_session['_csrf_token']


app.jinja_env.globals['csrf_token'] = generate_csrf_token


def loginStatusOutput():

    ''' Creates the html for a successful login '''
    output = ''
    output += '<h1>Welcome, '
    output += login_session['name']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['image']
    output += ' " style = "width: 300px; height: 300px;border-radius:\
            150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("You are now logged in as %s" % login_session['name'])

    return output


@app.route('/login')
def showLogin():

    ''' Returns the login page'''
    return render_template('login.html')


@app.route('/ajax/gconnect', methods=['POST'])
def gconnect():

    ''' Google API OAuth2 Authentication


        Obtain the authorization code.

        Try to upgrade the authorization code into a credentials object.
        Except on a FlowEchange Error and return the failure info in
        a json response.

        Check if the access token is valid.
        If there was an error in the access token info, abort.

        Verify that the access token is for the intended user.

        Verify that the access token is valid for this app.

        Store the access token in the session for later use.

        Get user info and store it in the session and return
        the html by invoking loginStatusOutput.

        TODO:  Create a template to show this information
    '''
    # Obtain the authorization code
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

    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'\
          % access_token
    r = requests.get(url)
    result = r.json()

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is for the intended user.
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
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
                        json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['provider'] = 'google'
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

    return loginStatusOutput()


def gdisconnect():

    ''' Revoke a current user's token.

        Only disconnects a connected user.

        If a successful response isn't returned the token is assumed
        invalid and the result from the request is returned as json.
    '''

    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token

    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps(result))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/ajax/fbconnect', methods=['POST'])
def fbconnect():

    ''' Facebook API OAuth2 Authentication


        Obtain the access_token submitted.

        Get the the app_id and app_secret from the json file.

        Send the access_token, app_id and app_secret to
        the authententication url to get back an access token.

        Strip the expiration tag from the token.

        Send the token to the user info url to get back
        the info for the authenticated user.

        Add the info to the session.

        Check if the user exists in the database.  If not,
        create the user.

        Return the html by invoking loginStatusOutput.

        TODO:  Create a template to show this information
    '''

    access_token = request.form.get('access_token')

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type='\
          'fb_exchange_token&client_id=%s&client_secret=%s&'\
          'fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['name'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # Strip out the equal sign before storing the token
    # for use in logout.
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&'\
          'height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['image'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return loginStatusOutput()


def fbdisconnect():
    ''' Disconnects Facebook login session

        Send back the access token and the facebook id
        to delete the token
    '''

    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'\
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "You have been logged out"


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():

    ''' Disconnects from the provider used for
        authentication.
    '''

    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()

            del login_session['gplus_id']

        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

        del login_session['access_token']
        del login_session['name']
        del login_session['email']
        del login_session['image']
        del login_session['user_id']
        del login_session['provider']

        flash("You have successfully been logged out.")

        return redirect(url_for('catalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('catalog'))


def createUser(login_session):

    ''' Creates a new user in the db'''

    newUser = User(name=login_session['name'], email=login_session[
                   'email'], image=login_session['image'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    ''' Returns the user for the provide user_id'''
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    ''' Returns the user_id for the provide email
        address. If no user is found with the address,
        None is returned
    '''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/feed')
def itemsATOM():

    ''' Returns an Atom feed of all items '''

    feed = AtomFeed(title="Imperial Catalog",
                    subtitle="A catalog of Galactice Empire items",
                    feed_url="http://localhost:8000/feed",
                    url="http://localhost:8000",
                    author="Sean Fallmann")

    categories = getAllCategories()
    for c in categories:
        for i in c.items:
            feed.add(
                category=c.name,
                title=i.name,
                id=i.id,
                content=i.description,
                content_type="html",
                author=i.user.name,
                url="http://localhost:8000/%s/%s" % (c.name, i.name),
                updated=datetime.datetime.utcnow(),
                )

    return feed


@app.route('/json/categories')
def categoriesJSON():

    ''' Returns all categories as json'''

    categories = getAllCategories()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/json/<category_name>/')
def categoryItemsJSON(category_name):

    ''' Returns all category items as json'''

    category_name = category_name.title()
    try:
        category = session.query(Category).filter(
                    Category.name == category_name).one()
        c = category.serialize
        c['items'] = [i.serialize for i in category.items]
        return jsonify(c)
    except NoResultFound:
        return "No category named %s found." % category_name


@app.route('/json/<category_name>/<item_name>')
def itemJSON(category_name, item_name):

    ''' Returns an item as json'''

    category_name = category_name.title()

    try:
        category = session.query(Category).filter(
                    Category.name == category_name).one()
    except NoResultFound:
        return "No category named %s found." % category_name

    try:
        item = session.query(Item).filter(
                Item.category_id == category.id).filter(
                Item.name == item_name).one()
        return jsonify(item.serialize)
    except NoResultFound:
        return "No item named %s found." % item_name


@app.route("/")
@app.route("/catalog")
@app.route("/catalog/category/<category>")
def catalog(category=None):

    ''' If a category name was passed in,
        query the db for a category with a matching name
        and get all the items for that category.

        Otherwise, set items to the 10 newest items across
        all categories.

        Return the rendered catalog template
    '''

    categories = getAllCategories()
    if category:
        category = session.query(Category).filter(
                   Category.name == category).one()
        items = category.items
    else:
        items = getLatestItems(10)

    return render_template('catalog.html', categories=categories,
                           items=items, category=category)


@app.route("/catalog/category/<category_name>/<item_name>")
def showItem(category_name=None, item_name=None):

    ''' Get the category_id from the name passed in.

        Then get the item from the category_id and
        the item name.

        Check if the "email" key is in login_session to determine
        if the request was made by an unauthenticated user or
        by a user other than the creator of the item, return
        the public template which doesn't include delete or
        update buttons.
    '''

    category_id = (session.query(Category).filter(
                   Category.name == category_name).one()).id
    item = session.query(Item).filter(Item.category_id == category_id).filter(
                    Item.name == item_name).one()

    if ('email' not in login_session or
       login_session['email'] != item.user.email):
        return render_template('p_item.html', item=item)
    else:
        return render_template('item.html', item=item)


@app.route("/catalog/additem", methods=['GET', 'POST'])
@app.route("/catalog/<category>/additem", methods=['GET', 'POST'])
def addItem(category=None):

    ''' Adds an item to the database.'''

    #  Checks to see if the user is authenticated
    #  If not, redirect to the catalog view
    if 'email' not in login_session:
        return redirect(url_for("catalog"))

    # Set error to None.  Error will be used for checking
    # the status of operations and displaying error information
    error = None
    user_id = getUserID(login_session['email'])

    # If the url had a value for category get the category
    if category:
        category = session.query(Category).filter(
                   Category.name == category).one()

    # Set categories to all categories
    categories = getAllCategories()

    if request.method == 'POST':

        # Get the values from the form
        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        # Check if the item name exists in the category.
        # If it does set error
        if item_name_used(category_id, name):
            error = "%s exists in the selected category."\
                    "Pick a different name" % name
        # Otherwise create the item
        else:
            item = Item(name=name,
                        description=description,
                        category_id=category_id,
                        user_id=user_id)

            session.add(item)
            session.commit()

            # Check if the form had a file
            if request.files['image']:
                # Set file to the uploaded file
                file = request.files['image']

                # Set success and error to the results of addItemFileFolder
                success, error = addItemFileFolder(
                                 file, item.category_id, item.id)

                # If it was successful, set item.image to the filename and
                # add the item to the db again to update it
                if success:
                    item.image = file.filename
                    session.add(item)
                    session.commit()
        # If there was an error return to add item page with the error
        if error:
            return render_template(
                   'add_item.html', categories=categories, error=error)
        # Otherwise, flash that the item was added and go the show item page
        # with the new item's info
        else:
            flash('Added %s!' % item.name)
            return redirect(url_for(
                            'showItem',
                            category_name=item.category.name,
                            item_name=item.name))
    # Returns the add item template on a GET request
    else:
        return render_template(
               'add_item.html', categories=categories, category=category)


@app.route("/catalog/category/<category_name>/<item_name>/update",
           methods=['GET', 'POST'])
def updateItem(category_name, item_name):

    ''' Updates an item in the database'''

    #  Checks to see if the user is authenticated
    #  If not, redirect to the catalog view
    if 'email' not in login_session:
        return redirect(url_for("catalog"))

    # Set error to None.  Error will be used for checking
    # the status of operations and displaying error information
    error = None

    category = session.query(Category).filter(
        Category.name == category_name).one()

    # Look for the item in the database.
    try:
        item = session.query(Item).filter(
               Item.category_id == category.id).filter(
               Item.name == item_name).one()

    # If it's not there set the error message and redirect
    # to the catalog view.
    except NoResultFound:
        error = "No item exists with name:%s category:%s"\
                % (item_name, category_name)
        return redirect(url_for('catalog', error=error))

    # Check if the authenticated user is the creator
    # of the item
    if login_session["email"] != item.user.email:
        # If not, redirect back to the item's page
        return redirect(url_for('showItem', category_name=item.category.name,
                                item_name=item.name))

    categories = getAllCategories()

    if request.method == 'POST':

        # Get the values from the form
        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        # Check if the item name exists in the category
        # and that it's not the name of the item being update.
        # Set the error message if the name is a duplicate
        if item_name_used(category_id, name) and name != item.name:
            error = "%s exists in the selected category.\
                     Pick a different name" % name

        # Otherwise update the values of the item
        else:
            item.name = name
            item.description = description
            old_category_id = item.category_id
            item.category_id = category_id

            # Check if the form had a file
            if request.files['image']:

                # Set file to the upload file
                file = request.files['image']

                # If the name of the new image is the
                # same as the current image
                # Prefix the new image filename with
                # 'copy_of_'.

                # Without this step, the new file name
                # would be deleted when cleanup occurs
                # to remove the old file since it had the
                # same name as the existing image.
                if item.image and item.image == file.filename:
                    file.filename = "copy_of_" + file.filename

                # Set success and error to the results of addItemFileFolder
                success, error = addItemFileFolder(file, category_id, item.id)

                if success:

                    # Checks if item.image has a value. If it does
                    # try removing the old file.
                    if item.image:
                        success, error = removeOldFile(
                                         old_category_id, item.id, item.image)

                    # Then if item.image has a value and the category_id
                    # of the item is different than the category_id prior to
                    # the update and file removal was successful, try removing
                    # the folder for the item's image.
                    elif (item.image and category_id != old_category_id and
                          success):
                        success, error = deleteItemFileFolder(
                                         old_category_id, item.id)

                    # If successful set item.image to the new filename.
                    if success:
                        item.image = file.filename

            # Check if the item has an image and the category id changed
            # but a new image wasn't uploaded
            elif item.image and category_id != old_category_id:

                # Get the value of the old folder and set the value of the new
                old_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/"\
                    % (old_category_id, item.id)
                new_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/"\
                    % (category_id, item.id)

                # Try moving the item folder under the new category folder
                try:
                    shutil.move(old_folder, new_folder)
                # If it fails, set the error
                except OSError:
                    error = "Error moving file folder"

            # Now the item changes can be commited to the db
            session.add(item)
            session.commit()

        # If there were errors return to the update page with the errors
        if error:
            return render_template('update_item.html', categories=categories,
                                   item=item, error=error)

        # Otherwise, go the the show item page with the updated item
        else:
            flash('Updated %s!' % item.name)
            return redirect(url_for(
                   'showItem',
                   category_name=item.category.name,
                   item_name=item.name))

    # Returns the update_item template on a GET request
    return render_template(
           'update_item.html', categories=categories, item=item)


@app.route("/catalog/category/<category_name>/<item_name>/delete",
           methods=['GET', 'POST'])
def deleteItem(category_name, item_name):

    ''' Delete an item in the database'''

    #  Checks to see if the user is authenticated
    #  If not, redirect to the catalog view
    if "email" not in login_session:
        return redirect(url_for("catalog"))

    # Set error to None.  Error will be used for checking
    # the status of operations and displaying error information
    error = None

    category = session.query(Category).filter(
                Category.name == category_name).one()

    # Look for the item in the database.
    try:
        item = session.query(Item).filter(
                Item.category_id == category.id).filter(
                Item.name == item_name).one()

    # If it's not there set the error message and redirect
    # to the catalog view.
    except NoResultFound:
        error = "No item exists with name:%s category:%s"\
                % (item_name, category_name)
        return redirect(url_for('catalog', error=error))

    categories = session.query(Category).all()

    if request.method == 'POST':

        # If the request user is not the creator redirect to the showItem view
        if login_session["email"] != item.user.email:
            return redirect(url_for("showItem", category_name=category_name,
                                    item_name=item_name))

        # Check if the item has an image.
        if item.image:

            # Get the success and error results from deleting the item folder
            success, error = deleteItemFileFolder(item.category.id, item.id)

            # If the deletion was successful set item.image to None
            if success:
                item.image = None

            # Otherwise redirect to the showItem view with the error
            else:
                return redirect(url_for('showItem',
                                        category_name=item.category.name,
                                        item_name=item.name, error=error))

        category = item.category.name
        deleted_name = item.name
        session.delete(item)
        session.commit()
        flash("%s deleted!" % deleted_name)
        return redirect(url_for('catalog', category=category))
    else:
        return redirect(url_for('showItem', category_name=item.category.name,
                                item_name=item.name, error=error))


@app.route('/uploads/<category_id>/<item_id>/<filename>')
def uploaded_file(category_id, item_id, filename):

    ''' Returns uploaded file for viewing '''

    item_folder = "/%s/%s/" % (category_id, item_id)
    folder = app.config['UPLOAD_FOLDER'] + item_folder

    return send_from_directory(folder,
                               filename)


def item_name_used(category_id, name):

    ''' Checks if the passed in name was used for an item
        within a category.
    '''

    try:
        item = session.query(Item).filter(
               Item.category_id == category_id).filter(Item.name == name).one()
        return True
    except NoResultFound:
        return False


def removeOldFile(category_id, item_id, filename):

    ''' Delete's a file based on the item_id, category_id and
        filename.
    '''

    success = False
    error = None

    # Files are located in folders based on category_id
    # and item_id.
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

    # Check if the file is an allowed type
    if allowed_file(file.filename):

        # Files are located in folders based on category_id
        # and item_id.
        item_folder = "/%s/%s/" % (category_id, item_id)
        folder = app.config['UPLOAD_FOLDER'] + item_folder

        # If the folder doesn't exist, create it.
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except OSError:
                error = "Error on creating file folder"
                return success, error

        # Try to save the file
        try:
            filename = secure_filename(file.filename)
            file.save(os.path.join(folder, filename))

        except:
            error = "Error on saving file"
            return success, error

        success = True
    else:
        error = "The filetype is not allowed."

    return success, error


def deleteItemFileFolder(category_id, item_id):

    ''' Remove a folder containing an item file '''

    success = False
    error = None

    # Try to remove the folder
    try:
        item_folder = "/%s/%s/" % (category_id, item_id)
        folder = app.config['UPLOAD_FOLDER'] + item_folder
        shutil.rmtree(folder)
        success = True
    except OSError:
        error = "Error removing folder"

    return success, error


def getAllCategories():
    ''' Returns all the categories in the database.'''
    return session.query(Category).all()


def getLatestItems(num):
    ''' Get the 10 newest items added to the database '''
    return session.query(Item).order_by(Item.created.desc())[:num]


if __name__ == '__main__':
    app.secret_key = random_string()
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
