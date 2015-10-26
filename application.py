import os, sys
import shutil
import random
import string
import requests
import httplib2
import json
from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash, make_response, Markup
from flask import session as login_session, send_from_directory
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from models import Base, User, Category, Item
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from werkzeug import secure_filename


# Default image for items obtained here
# http://www.clker.com/cliparts/q/L/P/Y/t/6/no-image-available-hi.png

APPLICATION_NAME = "Imperial Catalog"
APP_PATH = os.path.abspath('')
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads/')

DB_PATH = "sqlite:///%s/catalog.db" % APP_PATH
engine = create_engine(DB_PATH)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


#  From http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
def allowed_file(filename):
    return '.' in filename and \
           (filename.rsplit('.', 1)[1]).lower() in ALLOWED_EXTENSIONS


@app.route("/")
@app.route("/catalog")
@app.route("/catalog/category/<category>")
def catalog(category=None):


    categories = getAllCategories()
    if category:
        category = session.query(Category).filter(Category.name == category).one()
        items = category.items
    else:
        items = getLatestItems(10)


    return render_template('catalog.html', categories=categories,
                           items=items, category=category)


@app.route("/catalog/category/<category>/<item>")
def showItem(category=None, item=None):

    _category_id = (session.query(Category)
                    .filter(Category.name == category).one()).id
    _item = session.query(Item).filter(Item.category_id == _category_id)\
        .filter(Item.name == item).one()

    return render_template('item.html', item=_item)

@app.route("/catalog/additem", methods=['GET', 'POST'])
@app.route("/catalog/<category>/additem", methods=['GET', 'POST'])
def addItem(category=None):

    error = None

    if category:
        category = session.query(Category).filter(Category.name ==  category).one()

    categories = session.query(Category).all()


    if request.method == 'POST':

        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        if item_name_used(category_id, name):
            error = "%s exists in the selected category. Pick a different name" % name
        else:
            item = Item(name=name,description=description,category_id=category_id,user_id=1)
            session.add(item)
            session.commit()

            if request.files['image']:
                file = request.files['image']

                success, error = addItemFileFolder(file, item.category_id, item.id)

                if success:
                    item.image = file.filename
                    session.add(item)
                    session.commit()
        if error:
            return render_template('add_item.html', categories=categories, error=error)
        else:
            flash('ITEM ADDED!')
            return redirect(url_for('showItem', category=item.category.name, item=item.name))

    else:
        return render_template('add_item.html', categories=categories, category=category)




@app.route("/catalog/category/<category_name>/<item_name>/update", methods=['GET', 'POST'])
def updateItem(category_name, item_name):

    error = None
    category = session.query(Category).filter(Category.name == category_name).one()

    try:
        item = session.query(Item).filter(Item.category_id == category.id).filter(Item.name == item_name).one()
    except NoResultFound:
        item = None
        error = "No item exists with this name and category"

    categories = session.query(Category).all()

    if request.method == 'POST' and item is not None:

        name = request.form['name']
        description = request.form['description']
        category_id = request.form['category']

        if item_name_used(category_id, name) and name != item.name:
            error = "%s exists in the selected category. Pick a different name" % name
        else:

            item.name = name
            item.description = description
            old_category_id = item.category_id
            item.category_id = category_id

            if request.files['image']:
                file = request.files['image']

                if item.image and item.image == file.filename:
                    file.filename  = "copy_of_" + file.filename

                success, error = addItemFileFolder(file, item.category_id, item.id)
                if success:
                    if item.image:
                        success, error = removeOldFile(item.category_id, item.id, item.image)
                    elif item.image and category_id != old_category_id and success:
                        success, error = deleteItemFileFolder(old_category_id, item.id)
                    if success:
                        item.image = file.filename

            elif item.image and category_id != old_category_id:

                old_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/" % (old_category_id, item.id)
                new_folder = app.config['UPLOAD_FOLDER'] + "/%s/%s/" % (category_id, item.id)
                try:
                    shutil.move(old_folder, new_folder)
                except OSError:
                    error = "Error moving file folder"

            session.add(item)
            session.commit()

    return render_template('update_item.html', categories=categories, item=item, error=error)


@app.route("/catalog/category/<category_name>/<item_name>/delete", methods=['GET', 'POST'])
def deleteItem(category_name, item_name):

    error = None

    category = session.query(Category).filter(Category.name == category_name).one()

    try:
        item = session.query(Item).filter(Item.category_id == category.id).filter(Item.name == item_name).one()
    except NoResultFound:
        item = None
        error = "No item exists with this name and category"

    categories = session.query(Category).all()

    if request.method == 'POST' and item is not None:

        if item.image:
            success, error = deleteItemFileFolder(item.category.id, item.id)

            if success:
                item.image = None
            else:
                return redirect(url_for('showItem', category=item.category.name, item=item.name, error=error))

        category = item.category.name
        session.delete(item)
        session.commit()
        flash("Item deleted")
        return redirect(url_for('catalog', category=category))
    else:
        return redirect(url_for('showItem', category=item.category.name, item=item.name, error=error))


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

        if not os.path.exists(folder):

            try:
                os.makedirs(folder)
            except OSError:
                error = "Error on creating file folder"
                return success, error

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
    app.secret_key = '+_b)+_5hc3=7zc9xp_&ybw-#991k$p_dno#0wdu$=xppver)w4'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
