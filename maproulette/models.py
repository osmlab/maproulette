#!/usr/bin/python

from sqlalchemy import Column, Integer, String, Boolean, Float, Index, \
    ForeignKey, ForeignKeyConstraint, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
import sqlalchemy.types as types
from sqlalchemy.schema import UniqueConstraint
from geoalchemy2 import Geometry
from random import random
import datetime

Base = declarative_base()

class OSMUser(Base):
    __tablename__ = 'users'
    id = Column(Integer, unique=True, primary_key=True)
    oauth_token = Column(String)
    oauth_secret = Column(String)
    display_name = Column(String)
    home_location = Column(Geometry('POINT'))

    def __unicode__(self):
        return self.display_name

class Challenge(Base):
    __tablename__ = 'challenges'
    id = Column(Integer, unique=True, primary_key=True)
    slug = Column(String(72), primary_key=True)
    title = Column(String(128))
    description = Column(String)
    blurb = Column(String)
    polygon = Column(Geometry('POLYGON'))
    help = Column(String)
    instruction = Column(String)
    run = Column(String)
    active = Column(Boolean)
    Index('idx_geom', polygon, postgresql_using='gist')
    Index('idx_run', run)

    def __init__(self, slug):
        self.slug = slug

    def __unicode__(self):
        return self.slug

    def contains(self, point):
        """Test if a point (lat, lng) is inside the polygon of this challenge"""
        poly = Polygon(self.polygon)
        return poly.contains(point)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String(80), primary_key=True)
    challenge_id = Column(Integer, ForeignKey('challenges.id'),
                          primary_key=True)
    location = Column(Geometry('POINT'))
    run  = Column(String)
    random = Column(Float, default=random())
    manifest = Column(String)
    actions = relationship("Action")
    __table_args__ = (
        UniqueConstraint("id", "challenge_id"),
        )
    Index('idx_location', location, postgresql_using='gist')
    Index('idx_id', id)
    Index('idx_challenge', challenge_id)
    Index('idx_random', random)

    def __init__(self, challenge_id):
        self.challenge_id = challenge_id

class Action(Base):
    __tablename__ = 'actions'
    id = Column(Integer, unique=True, primary_key=True)
    timestamp = Column(DateTime, default = datetime.datetime.now())
    task_id = Column(String(80))
    challenge_id = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'))
    __table_args__ = (
        ForeignKeyConstraint(
            [task_id, challenge_id],
            [Task.id, Task.challenge_id]),
        {})    
    status = Column(String)
    
    def __init__(self, task_id, status, user_id = None):
        self.task_id = task_id
        self.status = status
        if user_id:
            self.user_id = user_id

if __name__ == "__main__":
	'''Create all tables'''
	engine = create_engine('postgresql://osm:osm@localhost/maproulette',
                               echo=True)
	Base.metadata.drop_all(engine)
	Base.metadata.create_all(engine)
