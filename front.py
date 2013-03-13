from flask import Flask, request, send_from_directory, jsonify, \
    render_template, Response, session, url_for, flash, redirect
from flask_oauth import OAuth
from hamlish_jinja import HamlishExtension
from flaskext.coffee import coffee
from ConfigParser import ConfigParser
import requests
from random import choice
from shapely.geometry import asShape, Point
import geojson
from xml.etree import ElementTree as ET
import sys

try:
    import settings
except ImportError:
    sys.stderr("""There must be a settings.py file with a secret_key.
Run bin/make_secret.py
""")
    sys.exit(2)

app = Flask(__name__)
app.secret_key = settings.secret_key
coffee(app)

# Add haml support
app.jinja_env.add_extension(HamlishExtension)
app.jinja_env.hamlish_mode = 'indented'
app.debug = True

# Load the configuration
config = ConfigParser({'host': '127.0.0.1'})
config.read('config.ini')

#initialize osm oauth
# instantiate OAuth object
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    base_url='http://openstreetmap.org/',
    request_token_url='http://www.openstreetmap.org/oauth/request_token',
    access_token_url='http://www.openstreetmap.org/oauth/access_token',
    authorize_url='http://www.openstreetmap.org/oauth/authorize',
    consumer_key='zoTZ4nLqQ1Y5ncemWkzvc3b3hG156jgvryIjiEkX',
    consumer_secret='e6nIgyAUqPt8d9kJymX6J86i5sG5mI8Rvv7XfRUb'
)

@osm.tokengetter
def get_osm_token(token=None):
    return session.get('osm_token')

# Grab the challenge metadata
challenges = {}
for challenge in config.sections():
    challenges[challenge] = {'port': config.get(challenge, 'port'),
                               'host': config.get(challenge, 'host')}
    meta = requests.get("http://%(host)s:%(port)s/meta" % {
            'host': config.get(challenge, 'host'),
            'port': config.get(challenge, 'port')}).json()
    challenges[challenge]['meta'] = meta
    challenges[challenge]['bounds'] = asShape(meta['polygon'])
    
# Some helper functions
def parse_user_details(s):
    """Takes a string XML representation of a user's details and
    returns a dictionary of values we care about"""
    root = ET.fromstring(s)
    user = {}
    user['id'] = root.find('./user').attribs['id']
    user['username'] = root.find('./user').attrib['display_name']
    try:
        user['lat'] = float(root.find('./user/home').attrib('lat'))
        user['lon'] = float(root.find('./user/home').attrib('lon'))
    except AttributeError:
        pass
    user['changesets'] = int(root.find('./user/changesets').attrib('count'))
    return user

def get_task(challenge, near = None, lock = True):
    """Gets a task and returns the resulting JSON as a string"""
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    args = ""
    if near:
        args += "near=%(near)s"
    if not lock:
        args += "lock=no"
    if args:
        url = "http://%(host)s:%(port)s/task?%(args)" % {
            'host': host,
            'port': port,
            'args': args}
    else:
        url = "http://%(host)s:%(port)s/task" % {
            'host': host,
            'port': port}
    r = requests.get(url)
    # Insert error checking here
    return r.text

def get_stats(challenge):
    """Gets the status of a challenge and returns it as a view"""
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/stats" % {
        'host': host,
        'port': port}
    r = requests.get(url)
    return make_json_response(r.text)

def get_meta(challenge):
    """Gets the metadata of a challenge and returns it as a view"""
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/stats" % {
        'host': host,
        'port': port}
    r = requests.get(url)
    return make_json_response(r.text)

def post_task(challenge, task_id, form):
    """Handles the challenge posting proxy functionality"""
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/task/%(task_id)s" % {
        'host': host,
        'port': port,
        'task_id': task_id}
    r = requests.post(url, data = form)
    return make_json_response(r.text)

def filter_task(difficulty = 'easy', point = None):
    """Returns matching challenges based on difficulty and area"""
    chgs = []
    for name, challenge in challenges.items():
        if challenge['meta']['difficulty'] == difficulty:
            if point:
                if challenge['bounds'].contains(point):
                    chgs.append(name)
            else:
               chgs.append(name)
    return chgs

def task_distance(task_text, point):
    """Accepts a task and a point and returns the distance between them"""
    # First we must turn the task into an object from text
    task = geojson.loads(task_text)
    # Now find the selected feature
    for feature in task['features']:
        if feature['selected'] is True:
            geom = asShape(feature)
            return geom.distance(point)

def closest_task(chgs, point):
    """Returns the closest task by a list of challenges"""
    # Transform point into coordinates
    coords = point.coords
    lat, lon = coords[0]
    latlng = "%f,%f" % (lat, lon)
    tasks = [get_task(chg, latlng) for chg in chgs]
    sorted_tasks = sorted(tasks, key=lambda task: task_distance(task, point))
    return sorted_tasks[0]

def make_json_response(json):
    """Takes text and returns it as a JSON response"""
    return Response(json.encode('utf8'), 200, mimetype = 'application/json')

# By default, send out the standard client
@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.haml')

@app.route('/challenges.html')
def challenges_web():
    "Returns the challenges template"
    return render_template('challenges.haml')

@app.route('/api/challenges')
def challenges_api():
    "Returns a list of challenges as json"
    chgs = [challenges[c].get('meta') for c in challenges]
    return jsonify({'challenges': chgs})

@app.route('/api/task')
def task():
    """Returns an appropriate task based on parameters"""
    # We need to find a task for the user to work on, based (as much
    # as possible)
    difficulty = request.args.get('difficulty', 'easy')
    near = request.args.get('near')
    if near:
        lat, lon = near.split(',')
        point = Point(lat, lon)
    else:
        point = None
    chgs = filter_task(difficulty, point)
    # We need code to test for an empty list here
    if near:
        task = closest_task(chgs, point)
    else:
        # Choose a random one
        challenge = choice(chgs)
        task = get_task(challenge)
    return make_json_response(task)
    
@app.route('/c/<challenge>/meta')
def challenge_meta(challenge):
    "Returns the metadata for a challenge"
    if challenge in challenges:
        return get_meta(challenge)
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/stats')
def challenge_stats(challenge):
    "Returns stat data for a challenge"
    if challenge in challenges:
        return get_stats(challenge)
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/task')
def challenge_task(challenge):
    "Returns a task for specified challenge"
    if challenge in challenges:
        task = get_task(get_task(challenge, request.args.get('near')))
        return make_json_response(task)
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/task/<id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    if challenge in challenges:
        dct = request.form
        return post_task(challenge, task_id, dct)
    else:
        return "No such challenge\n", 404

@app.route('/<path:path>')
def catch_all(path):
    "Returns static files based on path"
    return send_from_directory('static', path)

@app.route('/oauth/authorize')
def oauth_authorize():
    """Initiates OAuth authorization agains the OSM server"""
    return osm.authorize(callback=url_for('oauth_authorized',
      next=request.args.get('next') or request.referrer or None))

@app.route('/oauth/callback')
@osm.authorized_handler
def oauth_authorized(resp):
    """Receives the OAuth callback from OSM"""
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)
    session['osm_token'] = (
      resp['oauth_token'],
      resp['oauth_token_secret']
    )
    print(resp)
    flash('You were signed in')
    return redirect(next_url)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type = int, help = "the port to bind to",
                        default = 3000)
    parser.add_argument("--host", help = "the host to bind to",
                        default = "localhost")
    args = parser.parse_args()
    app.run(port=args.port)
    app.run(host=args.host, port=args.port)
