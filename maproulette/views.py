from maproulette import app
from flask import render_template, redirect, request, session

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
