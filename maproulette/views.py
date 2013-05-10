from maproulette import app, oauth, models
from flask import render_template, redirect, request, session, jsonify

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

@app.route('/api/challenges')
def challenges_api():
    "Returns a list of challenges as json"
    return jsonify(challenges=[i.slug for i in models.Challenge.query.all()])

@app.route('/api/challenge/<difficulty>')
def pick_challenge(difficulty):
    "Returns a random challenge based on the preferred difficulty"
    # I don't know if there is really a random() method..
    challenge = models.Challenge.query.filter(models.Challenge.difficulty==difficulty).random()
    return jsonify(challenge)
    
@app.route('/api/task/<challenge>/<lon>/<lat>/<distance>')
def task():
    if not challenge:
        # we will need something real here
        return None
    if lon and lat:
        models.Task.query.filter(models.Task.challenge_id == challenge)
    "Returns an appropriate task based on parameters"
    pass
    
@app.route('/api/c/<slug>/meta')
def challenge_meta(slug):
    "Returns the metadata for a challenge"
    challenge = get_challenge_or_404(slug)
    return jsonify(challenge = {
            'slug': challenge.slug,
            'title': challenge.title,
            'description': challenge.description,
            'blurb': challenge.blurb,
            'help': challenge.help,
            'instruction': challenge.instruction})

@app.route('/api/c/<challenge>/stats')
def challenge_stats(challenge):
    "Returns stat data for a challenge"
    ## THIS IS FAKE RIGHT NOW
    return jsonify({'total': 100, 'done': 50})

@app.route('/api/c/<slug>/task')
def challenge_task(slug):
    "Returns a task for specified challenge"
    challenge = get_challenge_or_404(slug)
    # Grab a random task (not very random right now)
    query = session.query(challenge.tasks)
    task = query.first()
    # Create a new status for this task
    action = Action(task, "assigned")
    action.save()
    return jsonify({
            'challenge': challenge.slug,
            'id': challenge.id,
            'features': task.manifest,
            'text': task.instruction})
 
@app.route('/api/c/<challenge>/task/<id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    pass

@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')
