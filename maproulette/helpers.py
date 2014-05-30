"""Some helper functions"""
from flask import abort, session, request, make_response
from maproulette.models import Challenge, Task, TaskGeometry
from maproulette.challengetypes import challenge_types
from functools import wraps
import json
from maproulette import app
from shapely.geometry import MultiPoint, asShape, Point
from random import random
from sqlalchemy.sql.expression import cast
from geoalchemy2.functions import ST_DWithin
from geoalchemy2.shape import from_shape
from geoalchemy2.types import Geography
import requests
import datetime


def signed_in():
    return "osm_token" in session


def osmerror(error, description):
    """Return an OSMError to the client"""
    payload = {'status': 555,
               'error': error,
               'description': description}
    response = make_response(json.dumps(payload), 555)
    return response


def get_or_abort(model, object_id, code=404):
    """Get an object with his given id
    or an abort error (404 is the default)"""
    result = model.query.get(object_id)
    return result or abort(code)


def get_challenge_or_404(challenge_slug, instance_type=None,
                         abort_if_inactive=True):
    """Return a challenge by its id or return 404.

    If instance_type is True, return the correct Challenge Type"""

    c = Challenge.query.filter(Challenge.slug == challenge_slug).first()
    if not c or (abort_if_inactive and not c.active):
        abort(404)
    if instance_type:
        challenge_class = challenge_types[c.type]
        challenge = challenge_class.query.filter(Challenge.id == c.id).first()
        return challenge
    else:
        return c


def challenge_exists(challenge_slug):
    q = Challenge.query.filter(
        Challenge.slug == challenge_slug).first()
    if q is None:
        return False
    return True


def get_task_or_404(challenge_slug, task_identifier):
    """Return a task based on its challenge and task identifier"""

    t = Task.query.filter(
        Task.challenge_slug == challenge_slug).filter(
        Task.identifier == task_identifier).first()
    if not t:
        abort(404)
    return t


def task_exists(challenge_slug, task_identifier):
    q = Task.query.filter(
        Task.challenge_slug == challenge_slug).filter(
        Task.identifier == task_identifier).first()
    if q is None:
        return False
    return True


def get_or_create_task(challenge, task_identifier):
    """Return a task, either pull a new one or create a new one"""

    task = (Task.identifier == task_identifier). \
        filter(Task.challenge_slug == challenge.slug).first()
    if not task:
        task = Task(challenge.id, task_identifier)
    return task


def require_signedin(f):
    """Require the caller to be authenticated against OSM"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not app.debug and not 'osm_token' in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def localonly(f):
    """Restricts the view to only localhost. If there is a proxy, it
    will handle that too"""

    @wraps(f)
    def decorated_function(*args, **hwargs):
        # FIXME request is not defined here
        if not request.headers.getlist("X-Forwarded-For"):
            ip = request.remote_addr
        else:
            ip = request.headers.getlist("X-Forwarded-For")[0]
        if not ip == "127.0.0.1":
            abort(404)


def get_random_task(challenge):
    """Get a random task"""

    rn = random()

    # get a random task. first pass
    q = Task.query.filter(Task.challenge_slug == challenge.slug,
                          Task.status.in_([
                              'available',
                              'skipped',
                              'created']),
                          Task.random >= rn).order_by(Task.random)
    q = refine_with_user_area(q)
    if q.first() is None:
        # we may not have gotten one if there is no task with
        # Task.random <= the random value. chance of this gets
        # bigger as the remaining available task number gets
        # smaller
        q = Task.query.filter(Task.challenge_slug == challenge.slug,
                              Task.status.in_([
                                  'available',
                                  'skipped',
                                  'created']),
                              Task.random < rn).order_by(Task.random)
    q = refine_with_user_area(q)
    return q.first() or None


def parse_task_json(data, slug, identifier, commit=True):
    """Parse task json coming in through the admin api"""

    task_geometries = []

    exists = task_exists(slug, identifier)

    # abort if the taskdata does not contain geometries and it's a new task
    if not 'geometries' in data:
        if not exists:
            abort(400)
    else:
        # extract the geometries
        geometries = data.pop('geometries')
        # parse the geometries
        for feature in geometries['features']:
            osmid = feature['properties'].get('osmid')
            shape = asShape(feature['geometry'])
            t = TaskGeometry(osmid, shape)
            task_geometries.append(t)

    # there's two possible scenarios:
    # 1.    An existing task gets an update, in that case
    #       we only need the identifier
    # 2.    A new task is inserted, in this case we need at
    #       least an identifier and encoded geometries.

    # now we check if the task exists
    if exists:
        # if it does, update it
        task = get_task_or_404(slug, identifier)
        if not task.update(data, task_geometries, commit=commit):
            abort(400)
    else:
        # if it does not, create it
        new_task = Task(slug, identifier)
        new_task.update(data, task_geometries, commit=commit)
    return True


def get_envelope(geoms):
    """returns the spatial envelope of a list of coordinate pairs
    in the form [(lon, lat), ...]"""
    return MultiPoint(geoms).envelope


def user_area_is_defined():
    return 'lon' and 'lat' and 'radius' in session


def refine_with_user_area(query):
    """Takes a query and refines it with a spatial constraint
    based on user setting"""
    if 'lon' and 'lat' and 'radius' in session:
        return query.filter(ST_DWithin(
            cast(Task.location, Geography),
            cast(from_shape(Point(session["lon"], session["lat"])), Geography),
            session["radius"]))
    else:
        return query


def send_email(to, subject, text):
    requests.post(
        "https://api.mailgun.net/v2/maproulette.org/messages",
        auth=("api", app.config["MAILGUN_API_KEY"]),
        data={"from": "MapRoulette <admin@maproulette.org>",
              "to": list(to),
              "subject": subject,
              "text": text})


def dict_from_tuples(tuples):
    # returns a nested dict for a tuple with three fields.
    # results are grouped by the first field
    result = {}
    for group in sorted(set([t[1] for t in tuples])):
        group = unix_time(group)
        for t in tuples:
            data = []
            if t[1] == group:
                data.append({unix_time(t[0]): t[2]})
        result[group] = data
    return result


# time in seconds from epoch
def unix_time(key):
    if isinstance(key, datetime.datetime):
        epoch = datetime.datetime.utcfromtimestamp(0)
        delta = key - epoch
        return delta.total_seconds()
    else:
        return key


class GeoPoint(object):

    """A geo-point class for use as a validation in the req parser"""

    def __init__(self, value):
        lon, lat = value.split('|')
        lat = float(lat)
        lon = float(lon)
        if not lat >= -90 and lat <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not lon >= -180 and lon <= 180:
            raise ValueError("longitude must be between -180 and 180")
        self.lat = lat
        self.lon = lon


class JsonData(object):

    """A simple class for use as a validation that a manifest is valid"""

    def __init__(self, value):
        self.data = json.loads(value)

    @property
    def json(self):
        return self.dumps(self.data)


class JsonTasks(object):

    """A class for validation of a mass tasks insert"""

    def __init__(self, value):
        data = json.loads(value)
        assert isinstance(data, list)
        for task in data:
            assert 'id' in task, "Task must contain an 'id' property"
            assert 'manifest' in task, \
                "Task must contain a 'manifest' property"
            assert 'location' in task, \
                "Task must contain a 'location' property"
        self.data = data
