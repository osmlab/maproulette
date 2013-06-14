from maproulette import app
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2.types import Geometry
from random import random
from datetime import datetime
from maproulette.database import db

class OSMUser(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    oauth_token = db.Column(db.String)
    oauth_secret = db.Column(db.String)
    display_name = db.Column(db.String)
    home_location = db.Column(Geometry('POINT'))

    def __unicode__(self):
        return self.display_name

# challenge
#  -tasks
#    -actions

# a challenge is like 'fix all highway tags' and does not belong to anything
# else - it has no foreign keys
class Challenge(db.Model):
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
    done_dialog = db.Column(db.String)
    editors = db.Column(db.String)
    template = db.Column(db.String, default = 'Default')
    templates = []
    db.Index('idx_geom', polygon, postgresql_using='gist')
    db.Index('idx_run', run)

    def __init__(self, slug):
        self.slug = slug

    def __unicode__(self):
        return self.slug

    def _get_task_available(self, task):
        """The function for a task to determine if it's available or not."""
        # Most tasks will use this method
        action = task.current_action
        if action.status = 'available':
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
        elif (current.status = 'alreadyfixed' or
            current.status = 'falsepositive'):
            l = [i for i in task.actions where i.status == "falsepositive" \
                     or i.status == "alreadyfixed"]
            if len(l) >= 2:
                task.status = 'done'
            else:
                task.status = 'available'
        else:
            # This is a catchall that a task should never get to
            task.status = 'available'
    
    @property
    def meta(self):
        """Return a dictionary of metadata for the challenge"""
        return {'slug': self.slug,
                'description': self.description,
                'help': self.help,
                'blurb': self.blurb,
                'instruction': self.instruction,
                'doneDlg': self.done_dialog,
                'editors': self.editors
                }

# a task is like 'fix this highway here' and belongs to a challenge
# and has actions associated with it
class Task(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    identifier = db.Column(db.String(72))
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'))
    location = db.Column(Geometry('POINT'))
    run  = db.Column(db.String(72))
    random = db.Column(db.Float, default=random())
    manifest = db.Column(db.String)
    actions = db.relationship("Action", lazy = 'dynamic')
    db.Index('idx_location', location, postgresql_using='gist')
    db.Index('idx_id', id)
    db.Index('idx_challenge', challenge_id)
    db.Index('idx_random', random)

    def __init__(self, challenge_id):
        self.challenge_id = challenge_id

    def near(self, lon,lat,distance):
        "Returns a task closer than <distance> (in deg) to a point"

    def checkout(self, osmid):
        """Checks out a task for a particular user"""
        action = Action(self.id, "assigned", osmid)
        self.current_action = action
        action.save()
        self.save()


# actions are associated with tasks and belong to users
class Action(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    timestamp = db.Column(db.DateTime, default = datetime.now())
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('osm_user.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    status = db.Column(db.String(32))

    def __init__(self, task_id, status, user_id = None):
        self.task_id = task_id
        self.status = status
        if user_id:
            self.user_id = user_id
