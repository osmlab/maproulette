from flask import Flask, session, request, send_from_directory, jsonify, \
    render_template, url_for, redirect
from helpers import make_json_response
from flask_oauth import OAuth
from simplekv.fs import FilesystemStore
from flaskext.kvsession import KVSessionExtension
from flaskext.coffee import coffee
from models import OSMUser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# ininiate database engine and create ORM session
engine = create_engine('postgresql://osm:osm@localhost/maproulette', echo=True)
Session = sessionmaker(bind=engine)
sqlalchemy_session = Session()

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
    return jsonify(challenges=[i.slug for i in Challenges.objects()])

@app.route('/api/task')
def task():
    """Returns an appropriate task based on parameters"""
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
    data = osm.get('user/details').data
    app.logger.debug("Getting user data from osm")
    if not data:
        return False
    else:
        osmid = data.find('user').attrib['id']
        # query for existing user
        if bool(sqlalchemy_session.query(OSMUser).filter(OSMUser.id==osmid).count()):
            #user exists
            user = sqlalchemy_session.query(OSMUser).filter(OSMUser.id==osmid).first()
            print('user found')
        else:
            # create new user
            user = OSMUser()
            user.id = usertree.attrib['id']
            user.display_name = usertree.attrib['display_name']
            hometree = usertree.find('home')
            if hometree is not None:
                user.home_location = 'POINT(%s %s)' % (hometree.attrib['lon'], hometree.attrib['lat'])
            else:
                print('no home for this user')
            sqlalchemy_session.add(user)
            sqlalchemy_session.commit()
            print('user created')
    session['display_name'] = user.display_name
    session['osm_id'] = user.id
    return redirect(next_url)
        
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
