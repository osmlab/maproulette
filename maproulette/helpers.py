"""Some helper functions"""
from xml.etree import ElementTree as ET
from flask import Response

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
    user = {}
    user['id'] = root.attrib['id']
    user['username'] = root.attrib['display_name']
    try:
        user['lat'] = float(root.find('./home').attrib['lat'])
        user['lon'] = float(root.find('./home').attrib['lon'])
    except AttributeError:
        pass
    user['changesets'] = int(root.find('./changesets').attrib['count'])
    return user
