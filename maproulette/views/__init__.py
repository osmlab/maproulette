"""The variosus views and routes for MapRoulette"""

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

class GeoJsonField(Raw):
    """A GeoJson Representation of an Shapely object"""

    def output(self, key, obj):
        value = get_value(key if self.attribute is None else self.attribute, obj)
        if value is None:
            return self.default
        else:
            value = geojson.loads(value)            
        return self.format(value)
        
challenge_fields = {'id': fields.String(attribute='slug'),
                    'title': fields.String,
                    'description': fields.String,
                    'blurb': fields.String,
                    'help': fields.String,
                    'instruction': fields.String,
                    'active': fields.Boolean,
                    'difficulty': fields.Integer,
                    'polygon': GeoJsonField}

task_fields = { 'id': fields.String(attribute='identifier'),
                'location': GeoJsonField,
                'manifest': GeoJsonField,
                'text': fields.String(attribute='instructions')}


# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

api = Api(app)

### CLIENT API ###
#
# This part of the API serves the MapRoulette client.
# All calls require the caller being authenticated against OSM


@app.route('/api/c/challenges')
def challenges():
    """returns a list of challenges as json
    optional URL parameters are
    difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
    contains: the coordinate to filter on (as lon|lat, returns only
    challenges whose bounding polygons contain this point)
    example: /api/c/challenges?contains=-100.22|40.45&difficulty=2
    """
    parser = reqparse.RequestParser()
    parser.add_argument('difficulty', type=int, choices=["1","2","3"],
                        help='difficulty cannot be parsed')
    parser.add_argument('contains', type=GeoPoint,
                        help="Could not parse contains")
    args = parser.parse_args()
    # Try to get difficulty from argument, or users prefers or default
    difficulty = args['difficulty'] or session.get('difficulty') or 1
    # Try to get location from argument or user prefs
    contains = None
    if args['contains']:
        contains = args['contains']
        coordWKT = 'POINT(%s %s)' % (contains.lat, contains.lon)
    elif 'home_location' in session:
        contains = session['home_location']
        coordWKT = 'POINT(%s %s)' % tuple(contains.split("|"))
        app.logger.debug('home location retrieved from session')
    query = db.session.query(Challenge)
    if difficulty:
        query = query.filter(Challenge.difficulty==difficulty)
    if contains:
        query = query.filter(Challenge.geom.ST_Contains(coordWKT))

    challenges = [marshal(challenge, challenge_fields)
                  for challenge in query.all() if challenge.active]
    #if there are no near challenges, return anything
    if len(challenges) == 0:
        app.logger.debug('we have nothing close, looking all over within difficulty setting')
        challenges = [marshal(challenge, challenge_fields)
                      for challenge in db.session.query(Challenge).\
                          filter(Challenge.difficulty==difficulty).all()
                      if challenge.active]
    # what if we still don't get anything? get anything!
    if len(challenges) == 0:
        app.logger.debug('we still have nothing, returning any challenge')
        challenges = [marshal(challenge, challenge_fields)
                      for challenge in db.session.query(Challenge).all()
                      if challenge.active]    
    app.logger.debug(challenges)
    return jsonify(challenges=challenges)


@app.route('/api/c/challenges/<challenge_slug>')
def challenge_by_slug(challenge_slug):
    """Returns the metadata for a challenge"""
    app.logger.debug('retrieving challenge %s' % (challenge_slug,))
    challenge = [marshal(
        get_challenge_or_404(challenge_slug),
        challenge_fields)]
    app.logger.debug(challenge)
    return jsonify(challenge=challenge)

@app.route('/api/c/challenges/<challenge_slug>/stats')
@osmlogin_required
def challenge_stats(challenge_slug):
    "Returns stat data for a challenge"
    challenge = get_challenge_or_404(challenge_slug, True)
    total = Task.query.filter(challenge_slug == challenge.slug).count()
    tasks = Task.query.filter(challenge_slug == challenge.slug).all()
    osmid = session.get('osm_id')
    logging.info("{user} requested challenge stats for {challenge}".format(
            user=osmid, challenge=challenge_slug))
    available = len([task for task in tasks
                     if challenge.task_available(task, osmid)])
    return jsonify(stats={'total': total, 'available': available})


@app.route('/api/c/challenges/<challenge_slug>/tasks')
@osmlogin_required
def challenge_tasks(challenge_slug):
    "Returns a task for specified challenge"
    challenge = get_challenge_or_404(challenge_slug, True)
    parser = reqparse.RequestParser()
    parser.add_argument('num', type=int, default=1,
                        help='Number of return results cannot be parsed')
    parser.add_argument('near', type=GeoPoint,
                        help='Near argument could not be parsed')
    parser.add_argument('assign', type=int, default=1,
                        help='Assign could not be parsed')
    args = parser.parse_args()
    osmid = session.get('osm_id')
    # By default, we return a single task, but no more than 10
    num = min(args['num'], 10)
    assign = args['assign']
    near = args['near']
    logging.info("{user} requesting {num} tasks from {challenge} near {near} assiging: {assign}".format(user=osmid, num=num, challenge=challenge_slug, near=near, assign=assign))
    task_list = []
    if near:
        coordWKT = 'POINT(%s %s)' % (near.lat, near.lon)
        task_query = Task.query.filter(Task.location.ST_Intersects(
                ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).limit(num)
        task_list = [task for task in task_query
                     if challenge.task_available(task, osmid)]
    if not near or not task_list:
        # If no location is specified, or no tasks were found, gather
        # random tasks
        task_list = [get_random_task(challenge) for _ in range(num)]
        task_list = filter(None, task_list)
        # If no tasks are found with this method, then this challenge
        # is complete
    if not task_list:
        # Is this the right error?
        osmerror("ChallengeComplete",
                 "Challenge {} is complete".format(challenge_slug))
    if assign:
        for task in task_list:
            action = Action(task.id, "assigned", osmid)
            task.current_state = action
            db.session.add(action)
            db.session.add(task)
        db.session.commit()
    logging.info(
        "{num} tasks found matching criteria".format(num=len(task_list)))
    tasks = [marshal(task, task_fields) for task in task_list]
    for query in get_debug_queries():
        app.logger.debug(query)
    return jsonify(tasks=tasks)

@app.route('/api/c/challenges/<challenge_slug>/tasks/<task_id>',
           methods=['GET', 'POST'])
@osmlogin_required
def task_by_id(challenge_slug, task_id):
    "Either displays a task (assigning it) or else posts the commit"
    # make sure we're authenticated
    challenge = get_challenge_or_404(challenge_slug, True)
    task = get_task_or_404(challenge, task_id)
    osmid = session.get('osm_id')
    if request.method == 'GET':
        try:
            assign = int(request.args.get('assign', 1))
        except ValueError:
            abort(400)
        if assign:
            action = Action(task.id, "assigned", osmid)
            task.current_state = action
            db.session.add(action)
            db.session.add(task)
        return jsonify(marshal(task, task_fields))

    elif request.method == 'POST':
        valid_actions = [button.action for button in challenge.dlg['buttons']]
        action = None
        for key in valid_actions:
            if request.form.get(key):
                action = Action(task.id, key, osmid)
                task.current_action = action
                db.session.add(action)
                break
        if not action:
            abort(400)
        new_state = challenge.task_status(task)
        action = Action(task.id, new_state, osmid)
        task.current_action = action
        db.session.add(action)
        db.session.add(task)
        db.commit()


@app.route('/logout')
def logout():
    # make sure we're authenticated
    if 'osm_token' in session or app.debug:
        session.destroy()
    return redirect('/')
