import os, sys
from flask import Flask, session, render_template, redirect
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee

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
app.config['SECRET_KEY'] = os.urandom(24)
app.debug = True

#from maproulette import views, models
from maproulette import models, views, oauth
from helpers import make_json_response

# connect flask app to server KV session store
KVSessionExtension(store, app)

# Coffeescript enable the app
coffee(app)
