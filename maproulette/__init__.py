import os, sys
from flask import Flask, session, render_template, redirect
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension

# initialize server KV session store
if not os.path.exists('./sessiondata'):
    os.makedirs('./sessiondata')
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
           static_folder = 'static',
           template_folder = 'templates',
           static_url_path = '/static')

from maproulette import config
app.config.from_object(config.DevelopmentConfig)

from maproulette import models, views, oauth, api

# connect flask app to server KV session store
KVSessionExtension(store, app)