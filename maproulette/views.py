"""The various views and routes for MapRoulette"""

import json
from flask import render_template, redirect, session, jsonify, abort, request
from flask.ext.sqlalchemy import get_debug_queries
from geoalchemy2.functions import ST_Contains, ST_Intersects, \
    ST_Buffer, ST_AsText
from geoalchemy2.shape import to_shape
from sqlalchemy import and_
from shapely.wkt import dumps
from maproulette import app
from maproulette.models import Challenge, Task, Action, db
from maproulette.helpers import *
from flask.ext.restful import reqparse


# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

### CLIENT API ###
#
# This part of the API serves the MapRoulette client.
# All calls require the caller being authenticated against OSM


@app.route('/api/c/challenges')
@osmlogin_required
def challenges():
    """returns a list of challenges as json
    optional URL parameters are
    difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
    contains: the coordinate to filter on (as lon|lat, returns only
    challenges whose bounding polygons contain this point)
    example: /api/c/challenges?contains=-100.22|40.45&difficulty=2
    """
    parser = reqparse.RequestParser()
    parser.add_argument('difficulty', type=int, choices=[1,2,3],
                        help='difficulty cannot be parsed')
    parser.add_argument('contains', type=GeoPoint,
                        help="Could not parse contains")
    args = parser.parse_args()
    # Try to get difficulty from argument, or users prefers or default
    difficulty = args['difficulty'] or user.difficulty or 1
    # Try to get location from argument or user prefs
    contains = None
    if args['contains']:
        contains = args['contains']
        coordWKT = 'POINT(%s %s)' % (contains.lat, contains.lon)
    elif 'home_location' in session:
        contains = session['home_location']
        coordWKT = 'POINT(%s %s)' % tuple(contains.split("|"))
        app.logger.debug('home location retrieved from session')
    query = session.query(Challenge)
    if difficulty:
        query = query.filter(Challenge.difficulty==difficulty)
    if contains:
        query = query.filter(polygon.ST_Contains(coordWKT))
    query = query.all()
    challenges = [challenge.id for challenge in query if challenge.active]
    app.logger.debug('returning %i challenges' % (len(challenges)))
    return jsonify(challenges=challenges)


@app.route('/api/c/challenges/<int:challenge_id>')
@osmlogin_required
def challenge_by_id(challenge_id):
    """Returns the metadata for a challenge"""
    challenge = get_challenge_or_404(challenge_id)
    return jsonify(challenge={
            'slug': challenge.slug,
            'title': challenge.title,
            'description': challenge.description,
            'blurb': challenge.blurb,
            'help': challenge.help,
            'doneDlg': json.loads(challenge.done_dialog),
            'help': challenge.instruction})


@app.route('/api/c/challenges/<int:challenge_id>/stats')
@osmlogin_required
def challenge_stats(challenge_id):
    "Returns stat data for a challenge"
    challenge = get_challenge_or_404(challenge_id, True)
    total = Task.query.filter(challenge_id == challenge.id).count()
    tasks = Task.query.filter(challenge_id == challenge.id).all()
    available = len([task for task in tasks
                     if challenge._get_task_available(task)])
    return jsonify(stats={'total': total, 'available': available})


@app.route('/api/c/challenges/<int:challenge_id>/tasks')
@osmlogin_required
def challenge_tasks(challenge_id):
    "Returns a task for specified challenge"
    challenge = get_challenge_or_404(challenge_id, True)
    parser = reqparse.RequestParser()
    parser.add_argument('num', type=int, default=1,
                        help='Number of return results cannot be parsed')
    parser.add_argument('near', type=GeoPoint,
                        help='Near argument could not be parsed')
    parser.add_argument('assign', type=int, default=1,
                        help='Assign could not be parsed')
    args = parser.parse_args()
    # By default, we return a single task, but no more than 10
    num = min(args['num'], 10)
    assign = args['assign']
    near = args['near']
    coordWKT = 'POINT(%s %s)' % (near.lat, near.lon)
    if near:
        task_query = Task.query.filter(Task.location.ST_Intersects(
                ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).limit(num)
        task_list = [task for task in task_query
                     if challenge._get_task_available(task)]
    else:
        task_list = [get_random_task(challenge) for i in range(num)]
        task_list = [task for task in task_list if task]
    if assign:
        for task in task_list:
            action = Action(task.id, "assigned", osmid)
            task.current_state = action
            db.session.add(action)
            db.session.add(task)
        db.session.commit()
    tasks = [{'id': task.identifier,
              'location': dumps(to_shape(task.location)),
              'manifest': task.manifest} for task in task_list]
    for query in get_debug_queries():
        app.logger.debug(query)
    return jsonify(tasks=tasks)


@app.route('/api/c/challenges/<challenge_id>/tasks/<task_id>',
           methods=['GET', 'POST'])
@osmlogin_required
def task_by_id(challenge_id, task_id):
    "Either displays a task (assigning it) or else posts the commit"
    # make sure we're authenticated
    challenge = get_challenge_or_404(challenge_id, True)
    task = get_task_or_404(challenge_id, task_id)
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
        return jsonify({'id': task.identifier,
                        'center': task.location,
                        'features': task.manifest,
                        'text': task.instruction})
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


### ADMINISTRATIVE API ###
@app.route('/api/a/challenges/<challenge_id>', methods=['POST'])
def challenge_settings(challenge_id):
    # FIXME other form of authentication required
    changeable = ['title', 'description', 'blurb', 'polygon', 'help',
                  'instruction', 'run', 'active']
    content = request.json['content']
    challenge = Challenge.query.filter(Challenge.id == challenge_id).\
        first_or_404()
    for key, value in content.items():
        if key in changeable:
            setattr(challenge, key, value)


@app.route('/api/a/challenges/<challenge_id>/tasks/<task_id>',
           methods=['PUT', 'POST'])
def edit_task(self, challenge_id, task_id):
    # FIXME other form of authentication required
    challenge = Challenge.query.filter(Challenge.id == challenge_id).\
        first_or_404()


@app.route('/logout')
def logout():
    # make sure we're authenticated
    if 'osm_token' in session or app.debug:
        session.destroy()
    return redirect('/')
