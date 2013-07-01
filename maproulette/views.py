import json

from maproulette import app, models
from maproulette.models import Challenge, Task, Action
from flask import render_template, redirect, session, jsonify, abort, request
from flask.ext.sqlalchemy import get_debug_queries
from geoalchemy2.functions import ST_Contains, ST_Intersects, ST_Buffer, ST_AsText
from geoalchemy2.shape import to_shape
from sqlalchemy import and_
from shapely.wkt import dumps

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

### CLIENT API ###

@app.route('/api/challenges')
def challenges_api():
    """returns a list of challenges as json
    optional URL parameters are
    difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
    contains: the coordinate to filter on (as lon|lat, returns only 
    challenges whose bounding polygons contain this point)
    example: /get/challenges?contains=-100.22|40.45&difficulty=2
    """    
    difficulty = request.args.get('difficulty')
    contains = request.args.get('contains')
    if contains:
        try:
            coordWKT = 'POINT(%s %s)' % tuple(contains.split("|"))
        except:
            contains = None
    if difficulty and contains:
        challenges =  Challenge.query.filter(and_(
            Challenge.difficulty == difficulty,
            Challenge.polygon.ST_Contains(coordWKT))).all()
    elif difficulty:
        challenges = Challenge.query.filter(
            Challenge.difficulty == difficulty).all()
    elif contains:
        challenges = Challenge.query.filter(
            Challenge.polygon.ST_Contains(coordWKT)).all()
    else:
        challenges = Challenge.query.all()
    return jsonify(challenges =
        [(i.id) for i in challenges if i.active])

@app.route('/api/challenges/<challenge_id>')
def challenge_details(challenge_id):
    "Returns details on the challenge"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    return jsonify(challenge=challenge)

@app.route('/api/challenges/<challenge_id>/meta')
def challenge_meta(challenge_id):
    "Returns the metadata for a challenge"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    return jsonify(challenge = {
            'slug': c.slug,
            'title': c.title,
            'description': c.description,
            'blurb': c.blurb,
            'help': c.help,
            'doneDlg': json.loads(c.done_dialog),
            'instruction': c.instruction})

@app.route('/api/challenges/<challenge_id>/stats')
def challenge_stats(challenge_id):
    "Returns stat data for a challenge"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    #challenge_obj = models.types[c.type](c.id)
    tasks = Task.query.filter(challenge_id==c.id).all()
    total = len(tasks)
    available = len([t for t in tasks if c._get_task_available(t)])
    return jsonify(stats={'total': 100, 'available': available})

# THIS FUNCTION IS NOT COMPLETE!!! #
@app.route('/api/challenges/<challenge_id>/tasks')
def challenge_task(challenge_id):
    "Returns a task for specified challenge"
    # By default, we return a single task
    num = request.args.get('num', 1)
    # If we don't have a "near", we'll use a random function
    near = request.args.get('near')
    try:
        coordWKT = 'POINT(%s %s)' % tuple(near.split("|"))
    except:
        near = None
    if near is not None:
        t = Task.query.filter(Task.location.ST_Intersects(ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).first()
    else:
        # FIXME return random tast
        abort(500)
    if not t.active:
        abort(503)
    # Each task we give should also be assigned
    # assign(task, osmid)

    for query in get_debug_queries():
        app.logger.debug(query)
        
    return jsonify(task = {
        'id': t.id,
        'identifier': t.identifier,
        'location': dumps(to_shape(t.location)),
        'manifest': t.manifest
        })

@app.route('/api/challenges/<challenge_id>/tasks/<task_id>')
def get_task_by_id(challenge, task_id):
    "Gets a specific task by ID"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    if not c.active:
        abort(503)

@app.route('/api/challenges/<challenge_id>/task/<task_id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    if not c.active:
        abort(503)

### CHALLENGE API ###

# List of items 
@app.route('/api/challenges/<challenge_id>', methods = ['POST'])
def challenge_settings(self, challenge_id):
    changeable = ['title', 'description', 'blurb', 'polygon', 'help',
                  'instruction', 'run', 'active']
    content = request.json['content']
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    # NEED SECURITY HERE!!!
    for k,v in content.items():
        if k in changeable:
            setattr(c,k,v)

@app.route('/api/challenges/<challenge_id>/tasks/<task_id>',
           methods = ['PUT', 'POST'])
def edit_task(self, challenge_id, task_id):
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    pass


@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')

