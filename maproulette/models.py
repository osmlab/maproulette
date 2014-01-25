  # """This file contains the SQLAlchemy ORM models"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, synonym
from sqlalchemy.ext.hybrid import hybrid_property
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
    """A MapRoulette User"""

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
    """A MapRoulette Challenge"""

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
        """Retrieve the polygon for this challenge, or return the World if there is none"""

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
        """Set the polygon for the challenge from a Shapely geometry"""

        self.geom = from_shape(shape)

    polygon = synonym('geom', descriptor=polygon)

    @property
    def tasks_available(self):
        """Return the number of tasks available for this challenge."""

        return Task.query.filter_by(
            available=True,
            challenge_slug=self.slug).count()

    @property
    def islocal(self):
        """Returns the localness of a challenge (is it small)"""

        # If the challange has no geometry, it is global
        if self.geom is None:
            return False
        # otherwise get the area and compare against local threshold
        area = db.session.query(self.geom.ST_Area()).one()[0]
        return (area <= app.config['MAX_SQ_DEGREES_FOR_LOCAL'])        


class Task(db.Model):
    """A MapRoulette task"""

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
    currentaction = db.Column(
        db.String)
    instruction = db.Column(
        db.String)
    available = db.Column(
        db.Boolean)
    challenge = db.relationship(
        "Challenge",
        backref=db.backref('tasks', order_by=id))
    # note that spatial indexes seem to be created automagically
    __table_args__ = (
        db.Index('idx_id', id),
        db.Index('idx_identifer', identifier),
        db.Index('idx_challenge', challenge_slug),
        db.Index('idx_random', random))

    def __init__(self, challenge_slug, identifier):
        self.challenge_slug = challenge_slug
        self.identifier = identifier
        self.append_action(Action('created'))
        self.available = True

    def __repr__(self):
        return '<Task %s>' % (self.identifier)

    @property
    def location(self):
        """Return the location for this task as a Shapely geometry"""

        return self.geometries[0].geom

    @location.setter
    def location(self, shape):
        """Set the location for this task from a Shapely object"""

        self.geom = from_shape(shape)

    location = synonym('geom', descriptor=location)

    def append_action(self, action):
        self.actions.append(action)
        self.currentaction = action.status

    def update(self, new_values):
        """This updates a task based on a dict with new values"""
        app.logger.debug('updating task %s ' % (self.identifier))
        for k,v in new_values.iteritems():
            app.logger.debug('updating %s to %s' % (k,v))
            if not hasattr(self, k):
                return False
            setattr(self, k, v)
            db.session.add(self)
            db.session.commit()
            return True


class TaskGeometry(db.Model):
    """The collection of geometries (1+) belonging to a task"""

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
        """Return the task geometry collection as a Shapely object"""

        return to_shape(self.geom)

    @geometry.setter
    def geometry(self, shape):
        """Set the task geometry collection from a Shapely object"""

        self.geom = from_shape(shape)

    geometry = synonym('geom', descriptor=geometry)


class Action(db.Model):
    """An action on a task"""

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
