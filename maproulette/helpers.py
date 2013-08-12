"""Some helper functions"""
from flask import abort, session
from maproulette.models import Challenge, Task, challenge_types
from functools import wraps
import random
import json

from maproulette import app

def osmerror(error, description):
    """Return an OSMError to the client"""
    abort(400, "%u: %u" % (error, description))

def get_challenge_or_404(challenge_id, instance_type=None,
                         abort_if_inactive=True):
    """Return a challenge by its id or return 404.

    If instance_type is True, return the correct Challenge Type
    """
    c = Challenge.query.filter(Challenge.id==challenge_id).first()
    if not c:
        abort(404, message="Challenge {} does not exist".format(challenge_id))
    if not c.active and abort_if_inactive:
        abort(503, message="Challenge {} is not active".format(challenge_id))
    if instance_type:
        return challenge_types[c.type].query.get(c.id)
    else:
        return c

def get_task_or_404(challenge, task_identifier):
    """Return a task based on its challenge and task identifier"""
    t = Task.query.filter(Task.identifier==task_identifier).\
        filter(Task.challenge_id==challenge.id).first()
    if not t:
        abort(404,"Task {} does not exist for {}".format(task_identifier,
                                                         challenge.slug))
    return t

def get_or_create_task(challenge, task_identifier):
    """Return a task, either pull a new one or create a new one"""
    task = (Task.identifier==task_identifier).\
        filter(Task.challenge_id==challenge.id).first()
    if not task:
        task = Task(challenge.id, task_identifier)
    return task

def osmlogin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not app.debug and not 'osm_token' in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def get_random_task(challenge):
    rn = random.random()
    t = Task.query.filter(Task.challenge_id == challenge.id,
                          Task.random <= rn).first()
    if not t:
        t = Task.query.filter(Task.challenge_id == challenge.id,
                              Task.random > rn).first()
    return t

class GeoPoint(object):
    """A geo-point class for use as a validation in the req parser"""
    def __init__(self, value):
        lon,lat = value.split('|')
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
        assert type(data) is list
        for task in data:
            assert 'id' in task, "Task must contain an 'id' property"
            assert 'manifest' in task, "Task must contain a 'manifest' property"
            assert 'location' in task, "Task must contain a 'location' property"
        self.data = data
