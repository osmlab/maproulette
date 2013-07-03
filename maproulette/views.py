"""The various views and routes for MapRoulette"""

import json
from flask import render_template, redirect, session, jsonify, abort, request
from flask.ext.sqlalchemy import get_debug_queries
from geoalchemy2.functions import ST_Contains, ST_Intersects, \
    ST_Buffer, ST_AsText
from geoalchemy2.shape import to_shape
from sqlalchemy import and_
from shapely.wkt import dumps
from maproulette import app, models
from maproulette.models import Challenge, Task, Action
from maproulette.helpers import get_challenge_or_404, get_task_or_404

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

@app.route('/api/c/challenges')
def challenges_api():
    """returns a list of challenges as json
    optional URL parameters are
    difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
    contains: the coordinate to filter on (as lon|lat, returns only 
    challenges whose bounding polygons contain this point)
    example: /get/challenges?contains=-100.22|40.45&difficulty=2
    """    
    if not session['osm_token']:
        abort(401)
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
        app.logger.debug('returning %i challenges' % (len(challenges)))
    elif difficulty:
        challenges = Challenge.query.filter(
            Challenge.difficulty == difficulty).all()
    elif contains:
        challenges = Challenge.query.filter(
            Challenge.polygon.ST_Contains(coordWKT)).all()
    else:
        challenges = Challenge.query.all()
    return jsonify(challenges =
        [i.id for i in challenges if i.active])

@app.route('/api/c/challenges/<challenge_id>')
def challenge(challenge_id):
    "Returns the metadata for a challenge"
    c = get_challenge_or_404(challenge_id)
    return jsonify(challenge = {
            'slug': c.slug,
            'title': c.title,
            'description': c.description,
            'blurb': c.blurb,
            'help': c.help,
            'doneDlg': json.loads(c.done_dialog),
            'instruction': c.instruction})

@app.route('/api/c/challenges/<challenge_id>/stats')
def challenge_stats(challenge_id):
    "Returns stat data for a challenge"
    c = get_challenge_or_404(challenge_id, True)
    total = Task.query.filter(challenge_id==c.id).count()
    tasks = Task.query.filter(challenge_id==c.id).all()
    available = len([t for t in tasks if c._get_task_available(t)])
    return jsonify(stats={'total': total, 'available': available})

# THIS FUNCTION IS NOT COMPLETE!!! #
@app.route('/api/c/challenges/<challenge_id>/tasks')
def challenge_tasks(challenge_id):
    "Returns a task for specified challenge"
    c = get_challenge_or_404(challenge_id, True)
    # By default, we return a single task
    num = request.args.get('num', 1)
    # If we don't have a "near", we'll use a random function
    near = request.args.get('near')
    try:
        coordWKT = 'POINT(%s %s)' % tuple(near.split("|"))
    except:
        near = None
    if near is not None:
        tq = Task.query.filter(Task.location.ST_Intersects(\
                ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).limit(num)
        tq = [t for t in tq if c._get_task_available(t)]
    else:
        # FIXME return random tast
        abort(500)
    # FIXME need to check for active state.
    #if not t[0].current_state == 'active':
    #    abort(503)
    # Any task given to the user should be assigned
    for t in tq:
        a = Action(t.id, "assigned", osmid)
        t.current_state = a
        db.session.add(a)
        db.session.add(t)
    db.session.commit()

    tasks = [{'id': t.identifier,
              'location': dumps(to_shape(t.location)),
              'manifest': t.manifest} for t in tq]
    # Each task we give should also be assigned
    # assign(task, osmid)
    
    for query in get_debug_queries():
        app.logger.debug(query)
    return jsonify(tasks = tasks)


@app.route('/api/c/challenges/<challenge_id>/tasks/<task_id>',
           methods=['GET', 'POST'])
def task(challenge, task_id):
    "Either displays a task (assigning it) or else posts the commit"
    c = get_challenge_or_404(challenge_id, True)
    t = get_task_or_404(challenge_id, task_id)
    if request.method == 'GET':
        try:
            assign = int(request.args.get('assign', 1))
        except ValueError:
            abort(417)
        if assign:
            a = Action(t.id, "assigned", osmid)
            t.current_state = a
            db.session.add(a)
            db.session.add(t)
        d = {'id': t.identifier,
             'center': t.location,
             'features': t.manifest}
        if t.instructions:
            d['instructions'] = t.instructions
        return jsonify(d)
    elif request.method == 'POST':
        valid_actions = [i.action for i in c.dlg['buttons']]
        a = None
        for k in valid_actions:
            if request.form.get(k):
                a = Action(t.id, k, osmid)
                t.current_action = a
                db.session.add(a)
                break
        if not a:
            # There was no valid action in the request
            ### WE SHOULD HANDLE THIS!!!
            return
        new_state = c.task_status(t)
        a = Action(t.id, new_state, osmid)
        t.current_action = a
        db.session.add(a)
        db.session.add(t)
        db.commit()

### ADMINISTRATIVE API ###

@app.route('/api/a/challenges/<challenge_id>', methods = ['POST'])
def challenge_settings(challenge_id):
    changeable = ['title', 'description', 'blurb', 'polygon', 'help',
                  'instruction', 'run', 'active']
    content = request.json['content']
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    for k, v in content.items():
        if k in changeable:
            setattr(c, k, v)

@app.route('/api/a/challenges/<challenge_id>/tasks/<task_id>',
           methods = ['PUT', 'POST'])
def edit_task(self, challenge_id, task_id):
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    pass


@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')
