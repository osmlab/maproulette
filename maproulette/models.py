import datetime
from flask import url_for
from maproulette import db

import re
from mongoengine.base import ValidationError
from mongoengine.fields import StringField

"""This module contains the various ORM models"""

# Mostly taken from
# https://github.com/bennylope/mongoengine-extras/blob/master/mongoengine_extras/fields.py
class SlugField(db.StringField):
    """A slug field"""
    slug_regex = re.compile(r"^[-\w]+$")
    def validate(self, s):
        # 72 + 182 (id length) + ':' = 255 total length for id 
        if not SlugField.slug_regex.match(s) or len(s) > 72:
            raise ValidationError("This string is not a slug: %s" % s)

class OSMUser(db.Document):
    user_id = db.IntField(primary_key=True)
    oauth_token = db.StringField()
    display_name = db.Stringfield()
    home_location = db.GeoPointfield()

    def __unicode__(self):
        return self.display_name

class Challenge(db.Document):
    slug = db.SlugField(primary_key = True)
    title = db.StringField(max_length=128)
    description = db.StringField()
    blurb = db.StringField()
    polygon = db.ListField(field=db.GeoPointField)
    help = db.StringField()
    tasks = db.ListField(db.EmbeddedDocumentField('Task'))
    instruction = db.StringField()
    run_id = db.StringField(max_length=64)
    active = db.BooleanField()
    meta = {
        'indexes': ['*polygon'],
    }
    
    def __unicode__(self):
        return self.title
    
class Task(db.Document):
    task_id = db.StringField(max_length = 255, primary_key = True)
    location = db.GeoPointField()
    taskactions = db.ListField(db.ReferenceField(db.TaskState))
    run_id  = db.StringField(max_length = 64)
    meta = {
        'allow_inheritance': True,
        'indexes': ['location']
        }

    @property
    def state(self):
        """Return the state of the task

        Available states: "available", "locked", "done", "deleted"
        """
        # First check for deletion or completion (this may need some
        # adjusting in the future, this is probably far too
        # complicated)
        for ts in self.taskactions:
            if ts.action == 'deleted':
                return 'deleted'
            elif ts.action == 'reviewed' or ts.action == 'edited':
                return 'done'
        # If none of those are the case, then we only need the most
        # recent taskaction
        ts = self.taskactions[0]
        if ts.action == 'available' or ts.action == 'skipped':
            return 'available'
        if ts.action == 'locked':
            now = datetime.datetime.now()
            if now - ts.timestamp > datetime.timedelta(minutes=30):
                # We should actually make a new TaskAction and set it here...
                return 'available'
            else:
                return 'locked'

class GeoTask(Task):
    geographies = db.EmbeddedDocument()
    instruction = db.StringField()

class TaskAction(db.DynamicDocument):
    ACTIONS = ('assigned', 'edited', 'reviewed', 'deleted',
               'notanerrored', 'skipped', 'alreadyfixed')
    ACTIONS_MAXLENGTH = max([len(i) for i in ACTIONS])
    action = db.StringField(choices = ACTIONS, max_length = ACTIONS_MAXLENGTH)
    task = db.ReferenceField(Task)
    timestamp = db.DateTimeField(default=datetime.datetime.now)
    osmuser = db.ReferenceField(OSMUser)
    meta = {
        'ordering': ['timestamp']
        }
 
