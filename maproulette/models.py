  # """This file contains the SQLAlchemy ORM models"""

from sqlalchemy import create_engine
from sqlalchemy.orm import synonym
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from geoalchemy2.shape import from_shape, to_shape
import random
from datetime import datetime
from maproulette import app
from shapely.geometry import Polygon, Point, MultiPoint
import pytz

# set up the ORM engine and database object
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                       convert_unicode=True)
Base = declarative_base()
db = SQLAlchemy(app)

random.seed()

world_polygon = Polygon([
    (-180, -90),
    (-180, 90),
    (180, 90),
    (180, -90),
    (-180, -90)])


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
        default="")
    blurb = db.Column(
        db.String,
        default="")
    geom = db.Column(
        Geometry('POLYGON'))
    help = db.Column(
        db.String,
        default="")
    instruction = db.Column(
        db.String,
        default="")
    active = db.Column(
        db.Boolean,
        nullable=False)
    difficulty = db.Column(
        db.SmallInteger,
        nullable=False,
        default=1)
    tasks = db.relationship(
        "Task",
        backref="challenges")
    type = db.Column(
        db.String,
        default='default',
        nullable=False)

##    @validates('slug')
##    def validate_slug(self, key, slug):
##        app.logger.debug("Slug passed in: " + slug)
##        app.logger.debug("Type: " + type(slug))
##        assert match('^[a-z0-9]+$', str(slug))
##        return slug

    # note that spatial indexes seem to be created automagically

    def __init__(self,
                 slug,
                 title,
                 geometry=None,
                 description=None,
                 blurb=None,
                 help=None,
                 instruction=None,
                 active=None,
                 difficulty=None):
        if geometry is None:
            geometry = world_polygon
        if active is None:
            active = False
        self.slug = slug
        self.title = title
        self.geometry = from_shape(geometry)
        self.description = description
        self.blurb = blurb
        self.help = help
        self.instruction = instruction
        self.active = active
        self.difficulty = difficulty

    def __unicode__(self):
        return self.slug

    def __repr__(self):
        return '<Challenge %s>' % self.slug

    @hybrid_property
    def polygon(self):
        """Retrieve the polygon for this challenge,
        or return the World if there is none"""

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

    @hybrid_property
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
        db.ForeignKey('challenges.slug', onupdate="cascade"))
    random = db.Column(
        db.Float,
        default=getrandom,
        nullable=False)
    manifest = db.Column(
        db.String)  # not used for now
    location = db.Column(
        Geometry)
    geometries = db.relationship(
        "TaskGeometry",
        cascade='all,delete-orphan',
        backref=db.backref("task"))
    actions = db.relationship(
        "Action",
        cascade='all,delete-orphan',
        backref=db.backref("task"))
    status = db.Column(
        db.String)
    instruction = db.Column(
        db.String)
    # note that spatial indexes seem to be created automagically
    __table_args__ = (
        db.Index('idx_id', id),
        db.Index('idx_identifer', identifier),
        db.Index('idx_challenge', challenge_slug),
        db.Index('idx_random', random))

    def __init__(self, challenge_slug, identifier, instruction=None):
        self.challenge_slug = challenge_slug
        self.identifier = identifier
        self.instruction = instruction
        self.append_action(Action('created'))

    def __repr__(self):
        return '<Task %s>' % (self.identifier)

    def __str__(self):
        return self.identifier

    @hybrid_method
    def has_status(self, statuses):
        if not type(statuses) == list:
            statuses = [statuses]
        return self.status in statuses

    @has_status.expression
    def has_status(cls, statuses):
        if not type(statuses) == list:
            statuses = [statuses]
        return cls.status.in_(statuses)

    def update(self, new_values, geometries, commit=True):
        """This updates a task based on a dict with new values"""
        for k, v in new_values.iteritems():
            # if a status is set, append an action
            if k == 'status':
                self.append_action(Action(v))
            elif not hasattr(self, k):
                app.logger.debug('task does not have %s' % (k,))
                return False
            setattr(self, k, v)

        self.geometries = []

        for geometry in geometries:
            self.geometries = geometries

        # set the location for this task, as a representative point of the
        # combined geometries.
        self.set_location()

        db.session.merge(self)
        if commit:
            db.session.commit()
        return True

    @property
    def is_within(self, lon, lat, radius):
        return self.location.intersects(Point(lon, lat).buffer(radius))

    def append_action(self, action):
        self.actions.append(action)
        # duplicate the action status string in the tasks table to save lookups
        self.status = action.status
        db.session.commit()

    def set_location(self):
        """Set the location of a task as a cheaply calculated
        representative point of the combined geometries."""
        # set the location field, which is a representative point
        # for the task's geometries
        # first, get all individual coordinates for the geometries
        coordinates = []
        for geometry in self.geometries:
            coordinates.extend(list(to_shape(geometry.geom).coords))
        # then, set the location to a representative point
        # (cheaper than centroid)
        self.location = from_shape(MultiPoint(
            coordinates).representative_point(), srid=4326)


class TaskGeometry(db.Model):

    """The collection of geometries (1+) belonging to a task"""

    __tablename__ = 'task_geometries'
    id = db.Column(
        db.Integer,
        nullable=False,
        unique=True,
        primary_key=True)
    osmid = db.Column(
        db.BigInteger)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id', onupdate="cascade"),
        nullable=False)
    geom = db.Column(
        Geometry,
        nullable=False)

    def __init__(self, osmid, shape):
        self.osmid = osmid
        self.geom = from_shape(shape)

    @hybrid_property
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
        # store the timestamp as naive UTC time
        default=datetime.now(pytz.utc).replace(tzinfo=None),
        nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', onupdate="cascade"))
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id', onupdate="cascade"))
    status = db.Column(
        db.String(),
        nullable=False)
    editor = db.Column(
        db.String())

    def __repr__(self):
        return "<Action %s set on %s>" % (self.status, self.timestamp)

    def __init__(self, status, user_id=None, editor=None):
        self.status = status
        # store the timestamp as naive UTC time
        self.timestamp = datetime.now(pytz.utc).replace(tzinfo=None)
        if user_id:
            self.user_id = user_id
        if editor:
            self.editor = editor
