import os, sys
from flask import Flask, session, request, send_from_directory, jsonify, \
    render_template, url_for, redirect
from flask_oauth import OAuth
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee
from flask.ext.sqlalchemy import SQLAlchemy

# check if secret.cfg exists
if not os.path.exists('secret.cfg'):
    print('''secret.cfg not found. You need to generate an app secret by
running ../bin/make_secret.py from the MR root directory''')
    exit()
    
# initialize server KV session store
if not os.path.exists('./sessiondata'):
	os.makedirs('./sessiondata')
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
           static_folder = 'static',
           template_folder = 'templates',
           static_url_path = '/static')

app.config.from_pyfile('maproulette.cfg')
app.config.from_pyfile('../secret.cfg')
app.secret_key = app.config['SECRET_KEY']
app.debug = True

db = SQLAlchemy(app)

#from maproulette import views, models
from maproulette import models
from helpers import make_json_response

# connect flask app to server KV session store
KVSessionExtension(store, app)

# Coffeescript enable the app
coffee(app)

# instantite OAuth object
# FIXME this should go into a separate oauth.py file.
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    base_url = app.config['OSM_URL'] + 'api/0.6/',
    request_token_url = app.config['OSM_URL'] + 'oauth/request_token',
    access_token_url = app.config['OSM_URL'] + 'oauth/access_token',
    authorize_url = app.config['OSM_URL'] + 'oauth/authorize',
    consumer_key = app.config['OAUTH_KEY'],
    consumer_secret = app.config['OAUTH_SECRET']
)

# FIXME this should go into a separate oauth.py file.
@osm.tokengetter
def get_osm_token(token=None):
    session.regenerate()
    return session.get('osm_token')

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')

@app.route('/api/challenges')
def challenges_api():
    "Returns a list of challenges as json"
    return jsonify(challenges=[i.slug for i in models.Challenges.objects()])

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

# FIXME this should go into a separate oauth.py file.
@app.route('/oauth/authorize')
def oauth_authorize():
    """Initiates OAuth authorization agains the OSM server"""
    return osm.authorize(callback=url_for('oauth_authorized',
      next=request.args.get('next') or request.referrer or None))

# FIXME this should go into a separate oauth.py file.
@app.route('/oauth/callback')
@osm.authorized_handler
def oauth_authorized(resp):
    """Receives the OAuth callback from OSM"""
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        return redirect(next_url)
    session['osm_token'] = (
      resp['oauth_token'],
      resp['oauth_token_secret']
    )
    data = osm.get('user/details').data
    app.logger.debug("Getting user data from osm")
    if not data:
        return False
    else:
        userxml = data.find('user')
        osmid = userxml.attrib['id']
        # query for existing user
        if bool(models.OSMUser.query.filter(models.OSMUser.id==osmid).count()):
            #user exists
            user = OSMUser.query.filter(OSMUser.id==osmid).first()
            print('user found')
        else:
            # create new user
            user = models.OSMUser()
            user.id = osmid
            user.display_name = userxml.attrib['display_name']
            homexml = userxml.find('home')
            if homexml is not None:
                user.home_location = 'POINT(%s %s)' % (homexml.attrib['lon'], homexml.attrib['lat'])
            else:
                print('no home for this user')
            db.session.add(user)
            db.session.commit()
            print('user created')
    session['display_name'] = user.display_name
    session['osm_id'] = user.id
    return redirect(next_url)
