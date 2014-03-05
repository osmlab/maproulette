  # !/usr/bin/env python

import os
import sys
import subprocess
from flask.ext.runner import Manager
from maproulette import app
from maproulette.models import db
from flask.ext.migrate import MigrateCommand, Migrate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

migrate = Migrate(app, db)

manager = Manager(app)

manager.add_command('db', MigrateCommand)


@manager.command
def clean_pyc():
    """Removes all *.pyc files from the project folder"""
    clean_command = "find . -name *.pyc -delete".split()
    subprocess.call(clean_command)


@manager.command
def drop_db():
    """Creates the database tables"""
    db.drop_all()


@manager.command
def create_db():
    """Creates the database tables"""
    db.create_all()

if __name__ == "__main__":
    manager.run()
