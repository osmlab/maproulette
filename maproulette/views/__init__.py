"""The various views and routes for MapRoulette"""

import json
import logging
from flask import render_template, redirect, session, abort, request, jsonify, json
from flask.ext.sqlalchemy import get_debug_queries
from geoalchemy2.functions import ST_Contains, ST_Intersects, \
    ST_Buffer, ST_AsText
from geoalchemy2.shape import to_shape
from sqlalchemy import and_
from shapely.wkt import dumps
from maproulette import app
from maproulette.models import Challenge, Task, Action, db
from maproulette.helpers import osmlogin_required, get_task_or_404, \
    GeoPoint, JsonData, JsonTasks, osmerror, get_random_task, \
    get_challenge_or_404
from flask.ext.restful import reqparse, fields, marshal_with, marshal
from flask.ext.restful.fields import get_value, Raw
from flask.ext.restful import Api
import geojson

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

@app.route('/logout')
def logout():
    # make sure we're authenticated
    if 'osm_token' in session or app.debug:
        session.destroy()
    return redirect('/')
