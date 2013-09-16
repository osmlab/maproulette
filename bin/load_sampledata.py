#!/usr/bin/env python

from maproulette.models import Challenge, Task
import simplejson as json
from shapely.wkt import dumps
from shapely.geometry import Point
from geoalchemy2.types import Geometry

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


def load_sampledata(path):

    identifier = 0
    tasks = []

    c = Challenge('test')
    c.title = 'Just a test challenge'
    c.active = True

    with open(path, 'rb') as filehandle:
        q = json.load(filehandle)

        for feature in q['features']:
            identifier += 1
            coordinates = feature['geometry']['coordinates']
            shape = Point(coordinates[0], coordinates[1])
            properties = feature['properties']
            t = Task('test',identifier)
            t.location = dumps(shape)
            t.run = 1
            tasks.append(t)
    
    print tasks
    
    feedengine = create_engine('postgresql://osm:osm@localhost/maproulette')

    Session = sessionmaker(bind=feedengine)

    session = Session()

    session.add(c)
    session.commit()
    for t in tasks:
        session.add(t)
    session.commit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('this requires a file argument')
    path = sys.argv[1]
    if not os.path.isfile(path):
        sys.exit('there is no file there')
    print 'working with %s' % (path,)
    load_sampledata(path)
