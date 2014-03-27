  # """This file contains the SQLAlchemy ORM models"""

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import synonym
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.declarative import declarative_base
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from geoalchemy2.shape import from_shape, to_shape
import random
from datetime import datetime
from maproulette import app
from flask import session
from shapely.geometry import Polygon
import pytz
from re import match
from sqlalchemy.orm import validates

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
    type = db.Column(
        db.String,
        default='default',
        nullable=False)

    @validates('slug')
    def validate_slug(self, key, slug):
        assert match('^[a-z0-9]+$', slug)
        return slug

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

    @property
    def approx_tasks_available(self):
        """Return the approximate number of tasks
        available for this challenge."""

        return len(
            [t for t in self.tasks if t.currentaction in [
                'created',
                'skipped',
                'available']])

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
        db.ForeignKey('challenges.slug'))
    random = db.Column(
        db.Float,
        default=getrandom,
        nullable=False)
    manifest = db.Column(
        db.String)  # deprecated
    geometries = db.relationship(
        "TaskGeometry",
        cascade='all,delete-orphan',
        backref=db.backref("task"))
    actions = db.relationship(
        "Action",
        cascade='all,delete-orphan',
        backref=db.backref("task"))
    currentaction = db.Column(
        db.String)
    instruction = db.Column(
        db.String)
    challenge = db.relationship(
        "Challenge",
        backref=db.backref('tasks', order_by=id))
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
        return self.currentaction in statuses

    @has_status.expression
    def has_status(cls, statuses):
        if not type(statuses) == list:
            statuses = [statuses]
        return cls.currentaction.in_(statuses)

    @hybrid_property
    def is_available(self):
        return self.has_status([
            'available',
            'created',
            'skipped']) or (self.has_status([
            'assigned',
            'editing']) and datetime.utcnow() -
            app.config['TASK_EXPIRATION_THRESHOLD'] >
            self.actions[-1].timestamp)

    # with currentactions as (select distinct on (task_id) timestamp,
    # status, task_id from actions order by task_id, id desc) select id,
    # challenge_slug from tasks join currentactions c on (id = task_id)
    # where c.status in ('available','skipped','created') or (c.status in
    # ('editing','assigned') and now() - c.timestamp > '1 hour');

    @is_available.expression
    def is_available(cls):
        # the common table expression
        current_actions = db.session.query(Action).distinct(
            Action.task_id).order_by(Action.task_id).order_by(
            Action.id.desc()).cte(
            name="current_actions", recursive=True)
        # before this time, a challenge is available even if it's
        # 'assigned' or 'editing'
        available_time = datetime.utcnow() -\
            app.config['TASK_EXPIRATION_THRESHOLD']
        res = cls.id.in_(
            db.session.query(Task.id).join(current_actions).filter(
                or_(
                    current_actions.c.status.in_([
                        'available',
                        'skipped',
                        'created']),
                    and_(
                        current_actions.c.status.in_([
                            'editing',
                            'assigned']),
                        available_time >
                        current_actions.c.timestamp))
            ))
        return res

    @hybrid_property
    def location(self):
        """Returns the location for this task as a Shapely geometry.
        This is meant to give the client a quick hint about where the
        task is located without having to transfer and decode the entire
        task geometry. In reality what we do is transmit the first
        geometry we find for the task. This is then parsed into a single
        representative lon/lat in the API by getting the first coordinate
        of the geometry retrieved here. See also the PointField class in
        the API code."""

        g = self.geometries[0].geom
        return to_shape(g)

    @location.setter
    def location(self, shape):
        """Set the location for this task from a Shapely object"""

        self.geom = from_shape(shape)

    def append_action(self, action):
        self.actions.append(action)
        # duplicate the action status string in the tasks table to save lookups
        self.currentaction = action.status
        if action.status == 'fixed':
            if self.validate_fixed():
                app.logger.debug('validated')
                self.append_action(Action('validated', session.get('osm_id')))

    def update(self, new_values, geometries):
        """This updates a task based on a dict with new values"""
        app.logger.debug(new_values)
        for k, v in new_values.iteritems():
            app.logger.debug('updating %s to %s' % (k, v))
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
        db.session.merge(self)
        db.session.commit()
        return True

    def validate_fixed(self):
        from maproulette.oauth import get_latest_changeset
        from maproulette.helpers import get_envelope
        import iso8601

        intersecting = False
        timeframe = False

        # get the latest changeset
        latest_changeset = get_latest_changeset(session.get('osm_id'))

        # check if the changeset bounding box covers the task geometries
        sw = (float(latest_changeset.get('min_lon')),
              float(latest_changeset.get('min_lat')))
        ne = (float(latest_changeset.get('max_lon')),
              float(latest_changeset.get('max_lat')))
        envelope = get_envelope([ne, sw])
        app.logger.debug(envelope)
        for geom in [to_shape(taskgeom.geom)
                     for taskgeom in self.geometries]:
            if geom.intersects(envelope):
                intersecting = True
                break

        app.logger.debug('intersecting: %s ' % (intersecting,))

        # check if the timestamp is between assigned and fixed
        assigned_action = Action.query.filter_by(
            task_id=self.id).filter_by(
            user_id=session.get('osm_id')).filter_by(
            status='assigned').first()

        # get assigned time in UTC
        assigned_timestamp = assigned_action.timestamp
        assigned_timestamp = assigned_timestamp.replace(tzinfo=pytz.utc)

        # get the timestamp when the changeset was closed in UTC
        changeset_closed_timestamp = iso8601.parse_date(
            latest_changeset.get('closed_at')).replace(tzinfo=pytz.utc)

        app.logger.debug(assigned_timestamp)
        app.logger.debug(changeset_closed_timestamp)
        app.logger.debug(datetime.now(pytz.utc))

        timeframe = assigned_timestamp <\
            changeset_closed_timestamp <\
            datetime.now(pytz.utc) + app.config['MAX_CHANGESET_OFFSET']

        app.logger.debug('timeframe: %s ' % (timeframe,))

        # check if the comment exists and contains 'maproulette'
        return intersecting and timeframe


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
        db.ForeignKey('tasks.id'),
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
        # store the timestamp as naive UTC time
        self.timestamp = datetime.now(pytz.utc).replace(tzinfo=None)
        if user_id:
            self.user_id = user_id
        if editor:
            self.editor = editor
