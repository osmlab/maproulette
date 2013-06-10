import json

from maproulette import app, models
from flask import render_template, redirect, session, jsonify, abort

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

def get_challenge_or_404(slug):
    return models.Challenge.query.filter_by(slug=slug).first_or_404()

@app.route('/api/challenges')
def challenges_api():
    "Returns a list of challenges as json"
    return jsonify(challenges =
        [i.slug for i in models.Challenge.query.all()])

@app.route('/api/challenges/<id>')
def challenge_details(id):
    "Returns details on the challenge"
    challenge = models.Challenge.query.filter(models.Challenge.id==id).first()
    if challenge:
        return jsonify(challenge=challenge)
    abort(404)

@app.route('/api/challenge/<difficulty>')
def pick_challenge(difficulty):
    "Returns a random challenge based on the preferred difficulty"
    # I don't know if there is really a random() method..
    challenge = models.Challenge.query.filter(models.Challenge.difficulty==difficulty).random()
    return jsonify(challenge=challenge)

@app.route('/api/task/<challenge>/<lon>/<lat>/<distance>')
def task():
    if not challenge:
        # we will need something real here
        return None
    if lon and lat:
        models.Task.query.filter(models.Task.challenge_id == challenge)
    "Returns an appropriate task based on parameters"
    pass

@app.route('/api/challenges/<slug>/meta')
def challenge_meta(slug):
    "Returns the metadata for a challenge"
    challenge = get_challenge_or_404(slug)
    return jsonify(challenge = {
            'slug': challenge.slug,
            'title': challenge.title,
            'description': challenge.description,
            'blurb': challenge.blurb,
            'help': challenge.help,
            'doneDlg': json.loads(challenge.done_dialog),
            'instruction': challenge.instruction})

@app.route('/api/challenges/<challenge>/stats')
def challenge_stats(challenge):
    "Returns stat data for a challenge"
    ## THIS IS FAKE RIGHT NOW
    return jsonify(stats={'total': 100, 'done': 50})

@app.route('/api/challenges/<slug>/task')
def challenge_task(slug):
    "Returns a task for specified challenge"
    challenge = get_challenge_or_404(slug)
    # Grab a random task (not very random right now)
    task = challenge.tasks.first()
    # Create a new status for this task
    action = models.Action(task.id, "assigned")
    models.db.session.add(action)
    models.db.session.commit()
    return jsonify(task = {
            'challenge': challenge.slug,
            'id': challenge.id,
            'features': task.manifest,
            'text': challenge.instruction})

@app.route('/api/challenges/<challenge>/task/<id>')
def get_task_by_id(challenge, task_id):
    "Gets a specific task by ID"
    pass

@app.route('/api/challenges/<challenge>/task/<id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    pass

@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')
