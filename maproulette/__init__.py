import os, sys
from flask import Flask, session, jsonify, \
    render_template, redirect
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee
from flask.ext.sqlalchemy import SQLAlchemy

# check if secret.cfg exists
if not os.path.exists('secret.cfg'):
    print('''secret.cfg not found. You need to generate an app secret by
running ../bin/make_secret.py from the MR root directory''')
    exit()
    
# initialize server KV session store
if not os.path.exists('./sessiondata'):
	os.makedirs('./sessiondata')
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
           static_folder = 'static',
           template_folder = 'templates',
           static_url_path = '/static')

app.config.from_pyfile('maproulette.cfg')
app.config.from_pyfile('../secret.cfg')
app.secret_key = app.config['SECRET_KEY']
app.debug = True

#from maproulette import views, models
from maproulette import models, views, oauth
from helpers import make_json_response

# connect flask app to server KV session store
KVSessionExtension(store, app)

# Coffeescript enable the app
coffee(app)
