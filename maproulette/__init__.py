import os
from flask import Flask
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension

# initialize server KV session store
if not os.path.exists('./sessiondata'):
    os.makedirs('./sessiondata')
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
            static_folder='static',
            template_folder='templates',
            static_url_path='/static')

from maproulette import config
# This is where you set MapRoulette's configuration mode
# Look at config/__init__.py for configuration classes

app.config.from_object(config.DevelopmentConfig)
#app.config.from_object(config.TestConfig)
#app.config.from_object(config.ProductionConfig)

# get the private stuff from a non-repo file specified
# in this envvar
app.config.from_envvar('MAPROULETTE_SECRET_SETTINGS')

if not app.debug:
    import logging
    logging.basicConfig(
        filename=app.config['LOGFILE'],
        level=logging.WARN)

from maproulette import models, views, oauth, api

# connect flask app to server KV session store
KVSessionExtension(store, app)
