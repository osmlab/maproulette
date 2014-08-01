import os
from flask import Flask
from simplekv.fs import FilesystemStore
from flask.ext.kvsession import KVSessionExtension
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy

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

# set up the ORM engine and database object
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                       convert_unicode=True)
Base = declarative_base()
db = SQLAlchemy(app)

if not app.debug:
    import logging
    logging.basicConfig(
        filename=app.config['LOGFILE'],
        level=app.config['LOGLEVEL'])

from maproulette import models, views, oauth, api

# connect flask app to server KV session store
KVSessionExtension(store, app)
