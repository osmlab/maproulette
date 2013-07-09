"""This file contains the SQLAlechemy ORM models"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from random import random
from datetime import datetime
from maproulette import app

# set up the ORM engine and database object
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                       convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()
db = SQLAlchemy(app)

challenge_types = {
    'default': []}


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    oauth_token = db.Column(db.String)
    oauth_secret = db.Column(db.String)
    display_name = db.Column(db.String)
    home_location = db.Column(Geometry('POINT'))
    languages = db.Column(db.String)
    changeset_count = db.Column(db.Integer)
    last_changeset_id = db.Column(db.Integer)
    last_changeset_date = db.Column(db.DateTime)
    last_changeset_bbox = db.Column(Geometry('POLYGON'))
    osm_account_created = db.Column(db.DateTime)
    difficulty = db.Column(db.SmallInteger)

    def __unicode__(self):
        return self.display_name


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    slug = db.Column(db.String(72), primary_key=True)
    title = db.Column(db.String(128))
    description = db.Column(db.String)
    blurb = db.Column(db.String)
    polygon = db.Column(Geometry('POLYGON'))
    help = db.Column(db.String)
    instruction = db.Column(db.String)
    run = db.Column(db.String(72))
    active = db.Column(db.Boolean)
    difficulty = db.Column(db.SmallInteger)
    type = db.Column(db.String, default='default')

    __table_args__ = (db.Index('idx_geom', polygon, postgresql_using='gist'),
                      db.Index('idx_run', run))

    def __init__(self, slug):
        self.slug = slug

    def __unicode__(self):
        return self.slug

    def _get_task_available(self, task):
        """The function for a task to determine if it's available or not."""
        action = task.current_action
        if action.status == 'available':
            return True
        else:
            return False

    def _set_task_status(self, task):
        """This is the function that runs after a task action is set,
        to set its secondary availability."""
        current = task.current
        if current.status == 'skipped':
            task.state = 'available'
        elif current.status == 'fixed':
            task.state = 'done'
        elif (current.status == 'alreadyfixed' or
              current.status == 'falsepositive'):
            l = [i for i in task.actions if i.status == "falsepositive"
                 or i.status == "alreadyfixed"]
            if len(l) >= 2:
                task.status = 'done'
            else:
                task.status = 'available'
        else:
            # This is a catchall that a task should never get to
            task.status = 'available'

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    identifier = db.Column(db.String(72))
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    location = db.Column(Geometry('POINT'))
    run = db.Column(db.String(72))
    random = db.Column(db.Float, default=random())
    manifest = db.Column(db.String)
    actions = db.relationship("Action", backref=db.backref("task"))
    instructions = db.Column(db.String())
    challenge = db.relationship("Challenge",
                                backref=db.backref('tasks', order_by=id))
    __table_args__ = (
        db.Index('idx_location', location, postgresql_using='gist'),
        db.Index('idx_id', id),
        db.Index('idx_challenge', challenge_id),
        db.Index('idx_random', random))

    def __init__(self, challenge_id, identifier):
        self.challenge_id = challenge_id
        self.identifier = identifier

    def __repr__(self):
        return '<Task %d>' % (self.id)

    def current_state(self):
        """Displays the current state of a task"""
        return self.current_action.state


class Action(db.Model):
    __tablename__ = 'actions'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    status = db.Column(db.String(32))

    def __init__(self, task_id, status, user_id=None):
        self.task_id = task_id
        self.status = status
        if user_id:
            self.user_id = user_id
