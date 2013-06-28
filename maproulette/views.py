import json

from maproulette import app, models
from maproulette.models import Challenge, Task, Action
from flask import render_template, redirect, session, jsonify, abort, request

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

### CLIENT API ###

@app.route('/api/challenges')
def challenges_api():
    "Returns a list of challenges as json"
    difficulty = request.args.get('difficulty')
    ### THIS USE OF NEAR IS PROBABLY BROKEN!!! ###
    near = request.args.get('near')
    if difficulty and near:
        challenges =  Challenge.query.filter_by(
            Challenge.difficulty==difficulty,
            Challenge.near == near).all()
    elif difficulty:
        challenges = Challenge.query.filter_by(
            Challenge.difficulty == difficulty).all()
    elif near:
        challenges = Challenge.query.filter_by(
            Challenge.near == near).all()
    else:
        challenges = Challenge.query.all()
    return jsonify(challenges =
        [i.slug for i in challenges if i.active])

@app.route('/api/challenges/<challenge_id>')
def challenge_details(challenge_id):
    "Returns details on the challenge"
    c = Challenge.query.filter(Challenge.id==challenge_id).first_or_404()
    return jsonify(challenge=challenge)

@app.route('/api/challenges/<challenge_id>/meta')
def challenge_meta(challenge_id):
    "Returns the metadata for a challenge"
    c = Challenge.query.filter_by(Challenge.id==challenge.id).first_or_404()
    return jsonify(challenge = {
            'slug': c.slug,
            'title': c.title,
            'description': c.description,
            'blurb': c.blurb,
            'help': challenge.help,
            'doneDlg': json.loads(c.done_dialog),
            'instruction': c.instruction})

@app.route('/api/challenges/<challenge_id>/stats')
def challenge_stats(challenge_id):
    "Returns stat data for a challenge"
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    challenge_obj = models.types[c.type](c.id)
    tasks = Tasks.query.filter_by(challenge_id==c.id)
    total = len(tasks)
    available = len([t for t in tasks if challenge_obj._get_task_available(t)])
    return jsonify(stats={'total': 100, 'available': available})

# THIS FUNCTION IS NOT COMPLETE!!! #
@app.route('/api/challenges/<challenge_id>/tasks')
def challenge_task(challenge_id):
    "Returns a task for specified challenge"
    # By default, we return a single task
    num = request.args.get('num', 1)
    # If we don't have a "near", we'll use a random function
    near = request.args.get('near')
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    if not c.active:
        abort(503)
    # Each task we give should also be assigned
    assign(task, osmid)
    return jsonify(tasks = [])

@app.route('/api/challenges/<challenge_id>/tasks/<task_id>')
def get_task_by_id(challenge, task_id):
    "Gets a specific task by ID"
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    if not c.active:
        abort(503)

@app.route('/api/challenges/<challenge_id>/task/<task_id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    if not c.active:
        abort(503)

### CHALLENGE API ###

# List of items 
@app.route('/api/challenges/<challenge_id>', methods = ['POST'])
def challenge_settings(self, challenge_id):
    changeable = ['title', 'description', 'blurb', 'polygon', 'help',
                  'instruction', 'run', 'active']
    content = request.json['content']
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    # NEED SECURITY HERE!!!
    for k,v in content.items():
        if k in changeable:
            setattr(c,k,v)

@app.route('/api/challenges/<challenge_id>/tasks/<task_id>',
           methods = ['PUT', 'POST'])
def edit_task(self, challenge_id, task_id):
    c = Challenge.query.filter_by(Challenge.slug==challenge_id).first_or_404()
    pass


@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')

