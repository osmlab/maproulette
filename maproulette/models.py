  # """This file contains the SQLAlchemy ORM models"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, synonym
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from geoalchemy2.shape import from_shape, to_shape
from geoalchemy2.functions import ST_Area
import random
from datetime import datetime
from maproulette import app
from shapely.geometry import Polygon

# set up the ORM engine and database object
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                       convert_unicode=True)
Base = declarative_base()
db = SQLAlchemy(app)

random.seed()

def getrandom():
    return random.random()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        unique=True,
        primary_key=True,
        nullable=False)
    oauth_token = db.Column(
        db.String)
    oauth_secret = db.Column(
        db.String)
    display_name = db.Column(
        db.String,
        nullable=False)
    home_location = db.Column(
        Geometry('POINT', management=True))
    languages = db.Column(
        db.String)
    changeset_count = db.Column(
        db.Integer)
    last_changeset_id = db.Column(
        db.Integer)
    last_changeset_date = db.Column(
        db.DateTime)
    last_changeset_bbox = db.Column(
        Geometry('POLYGON',
                 management=True))
    osm_account_created = db.Column(
        db.DateTime)
    difficulty = db.Column(
        db.SmallInteger)

    def __unicode__(self):
        return self.display_name


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id = db.Column(
        db.Integer,
        unique=True,
        primary_key=True,
        nullable=False)
    slug = db.Column(
        db.String(72),
        unique=True,
        primary_key=True,
        nullable=False)
    title = db.Column(
        db.String(128),
        nullable=False)
    description = db.Column(
        db.String,
        nullable=False)
    blurb = db.Column(
        db.String,
        nullable=False)
    geom = db.Column(
        Geometry('POLYGON'))
    help = db.Column(
        db.String,
        nullable=False)
    instruction = db.Column(
        db.String,
        nullable=False)
    run = db.Column(
        db.String(72))
    active = db.Column(
        db.Boolean,
        nullable=False)
    difficulty = db.Column(
        db.SmallInteger,
        nullable=False)
    type = db.Column(db.String, default='default', nullable=False)

    # note that spatial indexes seem to be created automagically
    __table_args__ = (db.Index('idx_run', run), )

    def __init__(self, slug):
        self.slug = slug
        self.geometry = Polygon

    def __unicode__(self):
        return self.slug

    @property
    def polygon(self):
        if self.geom is not None:
            return to_shape(self.geom)
        else:
            return Polygon([(-180, -90),
                            (-180, 90),
                            (180, 90),
                            (180, -90),
                            (-180, -90)])

    @polygon.setter
    def polygon(self, shape):
        self.geom = from_shape(shape)

    polygon = synonym('geom', descriptor=polygon)

    @property
    def islocal(self):
        # If the challange has no geometry, it is global 
        if self.geom is None:
            return False
        # otherwise get the area and compare against local threshold
        area = db.session.query(self.geom.ST_Area()).one()[0]
        return (area <= app.config['MAX_SQ_DEGREES_FOR_LOCAL'])

    def task_available(self, task, osmid=None):
        """The function for a task to determine if it's
        available or not."""
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

    id = db.Column(
        db.Integer,
        unique=True,
        primary_key=True,
        nullable=False)
    identifier = db.Column(
        db.String(72),
        nullable=False)
    challenge_slug = db.Column(
        db.String,
        db.ForeignKey('challenges.slug'))
    geom = db.Column(
        Geometry('POINT'),
        nullable=False)
    run = db.Column(
        db.String(72),
        nullable=False)
    random = db.Column(
        db.Float,
        default=getrandom,
        nullable=False)
    manifest = db.Column(
        db.String)  # deprecated
    geometries = db.relationship(
        "TaskGeometry",
        backref=db.backref("task"))
    actions = db.relationship(
        "Action",
        backref=db.backref("task"))
    instruction = db.Column(
        db.String())
    challenge = db.relationship(
        "Challenge",
        backref=db.backref('tasks', order_by=id))
    # note that spatial indexes seem to be created automagically
    __table_args__ = (
        db.Index('idx_id', id),
        db.Index('idx_challenge', challenge_slug),
        db.Index('idx_random', random))

    def __init__(self, challenge_slug, identifier):
        self.challenge_slug = challenge_slug
        self.identifier = identifier
        self.actions.append(Action('created'))

    def __repr__(self):
        return '<Task %s>' % (self.identifier)

    @property
    def current_action(self):
        return self.actions[-1]

    def current_state(self):
        """Displays the current state of a task"""
        return self.current_action.state

    @property
    def location(self):
        return to_shape(self.geom)

    @location.setter
    def location(self, shape):
        self.geom = from_shape(shape)

    location = synonym('geom', descriptor=location)


class TaskGeometry(db.Model):
    __tablename__ = 'task_geometries'
    osmid = db.Column(
        db.BigInteger,
        primary_key=True,
        nullable=False)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id'),
        nullable=False,
        primary_key=True)
    geom = db.Column(
        Geometry,
        nullable=False,
        primary_key=True)

    def __init__(self, osmid, shape):
        self.osmid = osmid
        self.geom = from_shape(shape)

    @property
    def geometry(self):
        return to_shape(self.geom)

    @geometry.setter
    def geometry(self, shape):
        self.geom = from_shape(shape)

    geometry = synonym('geom', descriptor=geometry)


class Action(db.Model):
    __tablename__ = 'actions'

    id = db.Column(
        db.Integer,
        unique=True,
        primary_key=True,
        nullable=False)
    timestamp = db.Column(
        db.DateTime,
        default=datetime.now,
        nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'))
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id'))
    status = db.Column(
        db.String(),
        nullable=False)
    editor = db.Column(
        db.String())

    def __repr__(self):
        return "<Action %s set on %s>" % (self.status, self.timestamp)

    def __init__(self, status, user_id=None, editor=None):
        self.status = status
        self.timestamp = datetime.now()
        if user_id:
            self.user_id = user_id
        if editor:
            self.editor = editor
