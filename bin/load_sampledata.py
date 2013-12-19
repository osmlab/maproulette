#!/usr/bin/env python

# This script loads a small set of fixtures into the MapRoulette database.
# It consists of a Challenge object and 463 Task objects with point
# geometries.
#
# To load make sure you have the database initialized. then just call
# this script.
#
# Right now (13/08/08), for this to work you need to patch Flask-SQLALchemy
# as described here: https://github.com/mitsuhiko/flask-sqlalchemy/pull/89

import sys
import os
from sqlalchemy import create_engine   
from sqlalchemy.orm import sessionmaker
from maproulette import app
from maproulette.models import Challenge, Task, Action, TaskGeometry
import simplejson as json
from shapely.geometry import Point
from geojson import dumps

def load_sampledata(datapath):
    '''
    Load the sample data from a file
    :param datapath: the datapath to the sample data file.
    '''

    identifier = 0
    tasks = []
    actions = []
    c = Challenge('test')
    c.slug = 'test'
    c.title = 'Just a test challenge'
    c.blurb = 'This challenge serves no purpose but to test everything'
    c.description = 'This challenge serves no purpose but to test everything'
    c.active = True
    c.difficulty = 1
    
    with open(datapath, 'rb') as filehandle:
        q = json.load(filehandle)

        for feature in q['features']:
            identifier += 1
            coordinates = feature['geometry']['coordinates']
            location = Point(coordinates[0], coordinates[1])
            t = Task('test', identifier)
            t.location = location
            t.geometries.append(TaskGeometry(location))
            t.run = 1
            a = Action(t.id, "created")
            tasks.append(t)
            
    print "%i tasks loaded..." % (identifier,)
    
    feedengine = create_engine('postgresql://osm:osm@localhost/maproulette_dev')

    Session = sessionmaker(bind=feedengine)

    session = Session()

    session.add(c)
    session.commit()
    for t in tasks:
        session.add(t)
    for a in actions:
        session.add(a)

    c.active = True
    session.commit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('this requires a file argument')
    path = sys.argv[1]
    if not os.path.isfile(path):
        sys.exit('there is no file there')
    print 'working with %s' % (path,)
    load_sampledata(path)
