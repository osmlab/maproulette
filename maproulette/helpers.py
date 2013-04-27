"""Some helper functions"""
from xml.etree import ElementTree as ET
from flask import Response

def make_json_response(json):
    """Takes text and returns it as a JSON response"""
    return Response(json.encode('utf8'), 200, mimetype = 'application/json')
