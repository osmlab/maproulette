"""This file contains the SQLAlchemy ORM models"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, synonym
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from geoalchemy2.functions import ST_AsGeoJSON
from geoalchemy2.shape import from_shape
import random
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

random.seed()

def getrandom():
    return random.random()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    oauth_token = db.Column(db.String)
    oauth_secret = db.Column(db.String)
    display_name = db.Column(db.String, nullable=False)
    home_location = db.Column(Geometry('POINT', management=True))
    languages = db.Column(db.String)
    changeset_count = db.Column(db.Integer)
    last_changeset_id = db.Column(db.Integer)
    last_changeset_date = db.Column(db.DateTime)
    last_changeset_bbox = db.Column(Geometry('POLYGON', management=True))
    osm_account_created = db.Column(db.DateTime)
    difficulty = db.Column(db.SmallInteger)

    def __unicode__(self):
        return self.display_name


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    slug = db.Column(db.String(72), unique=True, primary_key=True, nullable=False)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String)
    blurb = db.Column(db.String, nullable=False)
    geom = db.Column(Geometry('POLYGON'))
    helptext = db.Column(db.String)
    instruction = db.Column(db.String)
    run = db.Column(db.String(72))
    active = db.Column(db.Boolean, nullable=False)
    difficulty = db.Column(db.SmallInteger, nullable=False)
    type = db.Column(db.String, default='default', nullable=False)

    # note that spatial indexes seem to be created automagically
    __table_args__ = (db.Index('idx_run', run),)

    def __init__(self, slug):
        self.slug = slug

    def __unicode__(self):
        return self.slug
        
    @property
    def geometry(self):
        return ST_AsGeoJSON(self.geom)
    
    @geometry.setter
    def geometry(self, shape):
        self.geom = from_shape(shape)

    geometry = synonym('geom', descriptor=geometry)

    def task_available(self, task, osmid = None):
        """The function for a task to determine if it's available or not."""
        avail = False
        action = task.current_action
        if action.status == 'available':
            avail = True
        if not osmid:
            return avail
        # If osmid is present, then we will need to check every action
        # of this task against the previous actions
        for action in task.actions:
            # If it's just been assigned but no action was taken, we
            # can re-assign it, otherwise, we'll toss it
            if not action.status == 'assigned':
                return False
        return True

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    identifier = db.Column(db.String(72), nullable=False)
    challenge_slug = db.Column(db.String, db.ForeignKey('challenges.slug'))
    geom = db.Column(Geometry('POINT'), nullable=False)
    run = db.Column(db.String(72), nullable=False)
    random = db.Column(db.Float, default=getrandom, nullable=False)
    manifest = db.Column(db.String, nullable=False)
    actions = db.relationship("Action", backref=db.backref("task"))
    instructions = db.Column(db.String())
    challenge = db.relationship("Challenge",
                                backref=db.backref('tasks', order_by=id))
    # note that spatial indexes seem to be created automagically
    __table_args__ = (
        db.Index('idx_id', id),
        db.Index('idx_challenge', challenge_slug),
        db.Index('idx_random', random))

    def __init__(self, challenge_slug, identifier):
        self.challenge_slug = challenge_slug
        self.identifier = identifier

    def __repr__(self):
        return '<Task %d>' % (self.identifier)

    @property
    def current_action(self):
        return self.actions[-1]

    def current_state(self):
        """Displays the current state of a task"""
        return self.current_action.state

    @property
    def location(self):
        return ST_AsGeoJSON(self.geom)
    
    @location.setter
    def location(self, shape):
        self.geom = from_shape(shape)

    location = synonym('geom', descriptor=location)

class Action(db.Model):
    __tablename__ = 'actions'

    id = db.Column(db.Integer, unique=True, primary_key=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    status = db.Column(db.String(32), nullable=False)

    def __init__(self, task_id, status, user_id=None):
        self.task_id = task_id
        self.status = status
        if user_id:
            self.user_id = user_id
