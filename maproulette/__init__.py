import os
from flask import Flask
from simplekv.fs import FilesystemStore
from flask_kvsession import KVSessionExtension

# initialize server KV session store
if not os.path.exists('./sessiondata'):
    os.makedirs('./sessiondata')
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
            static_folder='static',
            template_folder='templates',
            static_url_path='/static')

# get configuration from a non-repo file specified
# in this envvar
app.config.from_envvar('MAPROULETTE_SETTINGS')

if not app.debug:
    import logging
    logging.basicConfig(
        filename=app.config['LOGFILE'],
        level=app.config['LOGLEVEL'])

from maproulette import models, views, oauth, api

# connect flask app to server KV session store
KVSessionExtension(store, app)
