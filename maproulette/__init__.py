from flask import Flask, session, request, send_from_directory, jsonify, \
    render_template, url_for, redirect
from helpers import make_json_response, parse_user_details
from flask_oauth import OAuth
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee
from random import choice
import geojson

import sys
from flask.ext.mongoengine import MongoEngine

try:
    import settings
    settings_keys = dir(settings)
except ImportError:
    sys.stderr.write("""There must be a settings.py file with a secret_key.
    Run bin/make_secret.py
    """)
    sys.exit(2)

# initialize server KV session store
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__)

# connect flask app to server KV session store
KVSessionExtension(store, app)

# Apps need a secret key
app.secret_key = settings.secret_key

# Coffeescript enable the app
coffee(app)

app.debug = True

# Adding MongoDB configs
app.config["MONGODB_SETTINGS"] = {'DB': "maproulette"}
db = MongoEngine(app)

#initialize osm oauth
# instantite OAuth object
oauth = OAuth()
if 'consumer_key' in settings_keys:
    consumer_key = settings.consumer_key
else:
    consumer_key = "consumer_key"

if 'consumer_secret' in settings_keys:
    consumer_secret = settings.consumer_secret
else:
    consumer_secret = "111111"
    
osm = oauth.remote_app(
    'osm',
    base_url='http://openstreetmap.org/',
    request_token_url = 'http://www.openstreetmap.org/oauth/request_token',
    access_token_url = 'http://www.openstreetmap.org/oauth/access_token',
    authorize_url = 'http://www.openstreetmap.org/oauth/authorize',
    consumer_key = consumer_key,
    consumer_secret = consumer_secret
)

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
    pass

@app.route('/api/task')
def task():
    """Returns an appropriate task based on parameters"""
    # We need to find a task for the user to work on, based (as much
    # as possible)
    difficulty = request.args.get('difficulty', 'easy')
    near = request.args.get('near')
    if near:
        lat, lon = near.split(',')
    else:
        point = None
    pass
    
@app.route('/api/c/<challenge>/meta')
def challenge_meta(challenge):
    "Returns the metadata for a challenge"
    pass

@app.route('/api/c/<challenge>/stats')
def challenge_stats(challenge):
    "Returns stat data for a challenge"
    pass

@app.route('/api/c/<challenge>/task')
def challenge_task(challenge):
    "Returns a task for specified challenge"
    pass

@app.route('/api/c/<challenge>/task/<id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    "Accepts data for completed task"
    pass

@app.route('/logout')
def logout():
    session.destroy()
    return redirect('/')

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
        return redirect(next_url)
    session['osm_token'] = (
      resp['oauth_token'],
      resp['oauth_token_secret']
    )
    print 'getting user data from osm'
    osmuserresp = osm.get('user/details')
    if osmuserresp.status == 200:
        session['user'] = get_user_attribs(osmuserresp.data)
    else:
        print 'not able to get osm user data'
    return redirect(next_url)

@app.route('/<path:path>')
def catch_all(path):
    "Returns static files based on path"
    return send_from_directory('static', path)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type = int, help = "the port to bind to",
                        default = 8080)
    parser.add_argument("--host", help = "the host to bind to",
                        default = "localhost")
    args = parser.parse_args()
    app.run(port=args.port)
    app.run(host=args.host, port=args.port)
