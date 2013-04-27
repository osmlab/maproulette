from flask import Flask, session, request, send_from_directory, jsonify, \
    render_template, url_for, redirect
from helpers import make_json_response, parse_user_details
from flask_oauth import OAuth
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee
from models import OSMUser
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# ininiate database engine and create ORM session
engine = create_engine('postgresql://osm:osm@localhost/maproulette', echo=True)
Session = sessionmaker(bind=engine)
sqlalchemy_session = Session()
user = OSMUser()

# initialize server KV session store
store = FilesystemStore('./sessiondata')

# instantiate flask app
app = Flask(__name__,
           static_folder = 'static',
           template_folder = 'templates',
           static_url_path = '/static')

app.config.from_pyfile('maproulette.cfg')

# connect flask app to server KV session store
KVSessionExtension(store, app)

# Apps need a secret key
app.secret_key = app.config['SECRET_KEY']

# Coffeescript enable the app
coffee(app)

app.debug = True

# instantite OAuth object
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    base_url='http://master.apis.dev.openstreetmap.org/api/0.6/',
    request_token_url = 'http://master.apis.dev.openstreetmap.org/oauth/request_token',
    access_token_url = 'http://master.apis.dev.openstreetmap.org/oauth/access_token',
    authorize_url = 'http://master.apis.dev.openstreetmap.org/oauth/authorize',
    consumer_key = app.config['OAUTH_KEY'],
    consumer_secret = app.config['OAUTH_SECRET']
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
    init_user()
    return redirect(next_url)

def init_user():
    print 'getting user data from osm'
    osmuserresp = osm.get('user/details')
    if osmuserresp.status == 200:
        if not osmuserresp.data:
            return False
        else:
            print('getting user details')
            usertree = osmuserresp.data.find('user')
            if not usertree:
                return False
            user.osmid = usertree.attrib['id']
            osmid = usertree.attrib['id']
            # query for existing user
            if bool(sqlalchemy_session.query(OSMUser).filter(OSMUser.id==osmid).count()):
                #user exists
                user = sqlalchemy_session.query(OSMUser).filter(OSMUser.id==osmid).first()
                print('user found')
            else:
                user = OSMUser()
                print('user created')
            user.id = osmid
            user.display_name = usertree.attrib['display_name']
            hometree = usertree.find('home')
            if hometree is not None:
                user.home_location = 'POINT(%s %s)' % (hometree.attrib['lon'], hometree.attrib['lat'])
            else:
                print('no home for this user')
            sqlalchemy_session.add(user)
            sqlalchemy_session.commit()
    else:
        print 'not able to get osm user data'
        print osmuserresp.status
        return False
    return True
        
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
