"""Some helper functions"""
from xml.etree import ElementTree as ET
from flask import Response
from maproulette.models import Challenge, Task
from maproulette import app
from maproulette.database import db

def make_json_response(json):
    """Takes text and returns it as a JSON response"""
    return Response(json.encode('utf8'), 200, mimetype = 'application/json')

def parse_user_details(s):
    """Takes a string XML representation of a user's details and
    returns a dictionary of values we care about"""
    root = ET.find('./user')
    if not root:
        print 'aaaargh'
        return None
    user = {
        'id': root.attrib['id'],
        'username': root.attrib['display_name']
    }
    try:
        user['lat'] = float(root.find('./home').attrib['lat'])
        user['lon'] = float(root.find('./home').attrib['lon'])
    except AttributeError:
        pass
    user['changesets'] = int(root.find('./changesets').attrib['count'])
    return user

def get_challenge_or_404(slug):
    """Return a challenge or 404"""
    # This is a little funky because it also gets the right 
    c = db.session.query(Challenge).get_by(slug=slug)
    if not c:
        abort(404)
    ctemplate = Challenge.templates[c.template]
    return db.session.query(ctemplate).get(c.id)
    

def get_task_or_404(challenge_slug, task_identifier):
    """Return a task or a 404"""
    challenge = get_challenge_or_404(challenge_slug)
    task = db.session.query(task).get_by(

    if not task:
        abort(404)
    return task
