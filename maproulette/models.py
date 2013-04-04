import datetime
from flask import url_for
from maproulette import db

import re
from mongoengine.base import ValidationError
from mongoengine.fields import StringField
from shapely.geometry import Polygon

"""This module contains the various ORM models"""

# Mostly taken from
# https://github.com/bennylope/mongoengine-extras/blob/master/mongoengine_extras/fields.py
class SlugField(db.StringField):
    """A slug field"""
    slug_regex = re.compile(r"^[-\w]+$")
    def validate(self, s):
        # 72 + 182 (id length) + ':' = 255 total length for id 
        if not SlugField.slug_regex.match(s):
            raise ValidationError("This string is not a slug: %s" % s)
        return super(SlugField, self).validate(s)

class IDField(db.StringField):
    """An ID field"""
    id_regex = re.compile(r"^[-_#\w]+$")
    def validate(self, s):
        # 72 + 182 (id length) + ':' = 255 total length for id 
        if not SlugField.slug_regex.match(s):
            raise ValidationError("This string is not a slug: %s" % s)
        return super(IDField, self).validate(s)

class OSMUser(db.Document):
    user_id = db.IntField(primary_key=True)
    oauth_token = db.StringField()
    display_name = db.StringField()
    home_location = db.GeoPointField()

    def __unicode__(self):
        return self.display_name

class Challenge(db.Document):
    slug = SlugField(primary_key = True, max_length = 72)
    title = db.StringField(max_length=128)
    description = db.StringField()
    blurb = db.StringField()
    polygon = db.ListField(field=db.GeoPointField)
    help = db.StringField()
    tasks = db.ListField(db.EmbeddedDocumentField('Task'))
    instruction = db.StringField()
    run = SlugField(max_length=64)
    active = db.BooleanField()
    meta = {
        'indexes': ['*polygon', 'run'],
    }
    
    def __unicode__(self):
        return self.slug
    
    def contains(self, point):
        """Test if a point (lat, lng) is inside the polygon of this challenge"""
        poly = Polygon(self.polygon)
        return poly.contains(point)

class Task(db.Document):
    identifier = IDField(max_length = 182, unique_with='challenge')
    challenge = db.ReferenceField(Challenge, required=True)
    location = db.GeoPointField()
    actions = db.EmbeddedDocumentField('TaskAction')
    run  = SlugField(max_length = 64)
    random = db.FloatField(default = random())
    meta = {
        'allow_inheritance': True,
        'indexes': ['location', 'identifier', 'challenge', 'random']
        }

    def __unicode__(self):
        return "%s:%s" % (self.challenge, self.identifier)

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
    geographies = db.DictField()
    instruction = db.StringField()

class Action(db.DynamicEmbeddedDocument):
    ACTIONS = ('assigned', 'edited', 'reviewed', 'deleted',
               'notanerrored', 'skipped', 'alreadyfixed')
    ACTIONS_MAXLENGTH = max([len(i) for i in ACTIONS])
    action = db.StringField(choices = ACTIONS, max_length = ACTIONS_MAXLENGTH,
                            required = True)
    task = db.ReferenceField(Task, required = True)
    timestamp = db.DateTimeField(default=datetime.datetime.now, required = True)
    osmuser = db.ReferenceField(OSMUser, required = True)
    meta = {
        'ordering': ['timestamp']
        }
