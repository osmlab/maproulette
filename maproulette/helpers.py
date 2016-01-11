"""Some helper functions"""
from flask import abort, session, request, make_response, Response
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
from datetime import datetime, timedelta
from sqlalchemy.sql import compiler
from psycopg2.extensions import adapt as sqlescape


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
    app.logger.debug('retrieving {}'.format(challenge_slug))
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

    t = get_task_or_none(challenge_slug, task_identifier)
    if t is None:
        abort(404)
    return t


def get_task_or_none(challenge_slug, task_identifier):
    """Return a task based on it's challenge and task identifier or none if not found"""

    t = Task.query.filter(
        Task.challenge_slug == challenge_slug).filter(
        Task.identifier == task_identifier).first()
    if not t:
        return None
    return t


def task_exists(challenge_slug, task_identifier):
    q = Task.query.filter(
        Task.challenge_slug == challenge_slug).filter(
        Task.identifier == task_identifier).first()
    if q is None:
        return False
    return True


def require_signedin(f):
    """Require the caller to be authenticated against OSM"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not app.debug and 'osm_token' not in session:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


def local_or_whitelist_only(f):
    """Restricts the view to only localhost or a whitelist defined in
    the app configuration. If there is a proxy, it will handle that too"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.headers.getlist("X-Forwarded-For"):
            ip = request.remote_addr
        else:
            ip = request.headers.getlist("X-Forwarded-For")[0]
        if not ip == "127.0.0.1" and ip not in app.config["IP_WHITELIST"]:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


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
    app.logger.debug(compile_query(q))
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


def json_to_task(slug, data, task=None, identifier=None):
    """Parse task json coming in through the admin api"""

    app.logger.debug(data)

    if identifier is None and task is None:
        if 'identifier' not in data:
            raise Exception('no identifier given')
        identifier = data['identifier']

    if task is None:
        # create the task if none was passed in
        try:
            task = Task(slug, identifier)
        except Exception, e:
            app.logger.warn(e.message)
            raise e
    else:
        # delete existing task geometries
        task.geometries = []

    # check for instruction
    if 'instruction' in data:
        task.instruction = data['instruction']
    # check for status
    if 'status' in data:
        task.status = data['status']

    # extract the task geometries
    if 'geometries' in data:
        geometries = data.pop('geometries')
        # parse the geometries
        for feature in geometries['features']:
            osmid = feature['properties'].get('osmid')
            shape = asShape(feature['geometry'])
            g = TaskGeometry(osmid, shape)
            task.geometries.append(g)
    return task


def geojson_to_task(slug, feature):
    """converts one geojson feature to a task.
    This will only work in a limited number of cases, where:
    * The geometry is one single Point or Linestring feature,
    * The OSM ID of the feature is in the id field of the JSON,
    and you are OK with the following:
    * The description cannot be set at the task level
    * The identifier will be slug-osmid"""
    # check for id and geometries
    if 'id' not in feature:
        app.logger.debug('no id in this feature, skipping')
        return None
    if 'geometry' not in feature:
        app.logger.debug('no geometries in feature, skipping')
        return None
    # generate an identifier
    osmid = feature['id']
    identifier = '{slug}-{osmid}'.format(
        slug=slug,
        osmid=osmid)
    # find, or create a task
    task = Task.query.filter(
        Task.challenge_slug == slug).filter(
        Task.identifier == identifier).first()
    if task is None:
        task = Task(slug, identifier)
        app.logger.debug('creating task {identifier}'.format(
            identifier=identifier))
    else:
        app.logger.debug('updating task {identifier}'.format(
            identifier=identifier))
        # clear existing geometries
        task.geometries = []
    # get the geometry
    geom = feature['geometry']
    shape = asShape(geom)
    try:
        g = TaskGeometry(osmid, shape)
        task.geometries.append(g)
        return task
    except Exception, e:
        app.logger.debug("task could not be created, {}".format(e))
        return None


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


# TODO this function is a mess.
def as_stats_dict(tuples, order=[0, 1, 2], start=None, end=None):
    # this parses three-field statistics query result in the form
    # [('status', datetime(2012, 05, 01, 12, 00), 12), ...]
    # into a dictionary that can easily be parsed by the charting client:
    # [{'key': 'status', values: {'date': value, ...}}, ...]
    # it takes into account the passed-in time slicing parameters and
    # pads the date range with missing values.
    result = []
    if len(tuples) == 0:
        return {}
    for group in sorted(set([t[order[0]] for t in tuples])):
        data = {}
        for t in tuples:
            if t[order[0]] == group:
                data[t[order[1]]] = t[order[2]]
        if isinstance(t[order[1]], datetime):
            start_in_data = min([t[order[1]] for t in tuples])
            end_in_data = max([t[order[1]] for t in tuples])
            if start is not None:
                start = min(start_in_data, start)
            else:
                start = start_in_data
            if end is not None:
                end = max(end_in_data, end)
            else:
                end = end_in_data
            data = pad_dates(start, end, data)
        result.append({
            "key": group,
            "values": data})
    return result


def pad_dates(start, end, data):
    result = {}
    days = (end - start).days if (end - start).days > 0 else 1
    for date in (start + timedelta(n) for n in range(days)):
        if date not in data.keys():
            result[parse_time(date)] = 0
        else:
            result[parse_time(date)] = data[date]
    return result


# time in seconds from epoch
def parse_time(key, unix_time=False):
    if isinstance(key, datetime):
        if unix_time:
            epoch = datetime.utcfromtimestamp(0)
            delta = key - epoch
            return delta.total_seconds()
        else:
            return key.isoformat()
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
        return json.dumps(self.data)


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


def compile_query(query):
    """
    Reconstructs the raw SQL query from an SQLAlchemy query object.

    :param query: SQLAlchemy query objext
    :return: The raw SQL query as a string.
    """
    dialect = query.session.bind.dialect
    statement = query.statement
    comp = compiler.SQLCompiler(dialect, statement)
    comp.compile()
    enc = dialect.encoding
    params = {}
    for k, v in comp.params.iteritems():
        if isinstance(v, unicode):
            v = v.encode(enc)
        params[k] = sqlescape(v)
    return (comp.string.encode(enc) % params).decode(enc)


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == app.config['AUTHORIZED_USER'] and password == app.config['AUTHORIZED_PASSWORD']


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        status=401,
        headers={'WWW-Authenticate': 'Basic realm="Login Required"'})


# authentication function wrapper. will require authentication on decorated functions unless we're on localhost.
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        app.logger.debug(request.url)
        if not is_localhost(request.url) and (not auth or not check_auth(auth.username, auth.password)):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


# determines if a URL is localhost
def is_localhost(url):
    from urlparse import urlparse
    return urlparse(url).hostname == 'localhost'
