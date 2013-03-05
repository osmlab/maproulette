from flask import Flask, request, abort, send_from_directory, jsonify, render_template, Response
from hamlish_jinja import HamlishExtension
from flaskext.coffee import coffee
from markdown import markdown
from ConfigParser import ConfigParser
import requests

import settings

from pprint import pprint

app = Flask(__name__)

# Add haml support
app.jinja_env.add_extension(HamlishExtension)
app.jinja_env.hamlish_mode = 'indented'
app.debug = True

# Load the configuration
config = ConfigParser({'host': '127.0.0.1'})
config.read('config.ini')

# Some helper functions
def get_task(challenge, near = None):
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    if near:
        url = "http://%(host)s:%(port)s/task?near=%(near)" % {
            'host': host,
            'port': port,
            'near': near}
    else:
        url = "http://%(host)s:%(port)s/task" % {
            'host': host,
            'port': port}
    r = requests.get(url)
    # Insert error checking here
    return make_json_response(r.text)

def get_stats(challenge):
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/stats" % {
        'host': host,
        'port': port}
    r = requests.get(url)
    return make_json_response(r.text)

def get_meta(challenge):
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/stats" % {
        'host': host,
        'port': port}
    r = requests.get(url)
    return make_json_response(r.text)

def post_task(challenge, task_id, form):
    host = config.get(challenge, 'host')
    port = config.get(challenge, 'port')
    url = "http://%(host)s:%(port)s/task/$(task_id)s" % {
        'host': host,
        'port': port,
        'id': task_id}
    r = requests.post(url, data = form)
    return make_json_response(r.text)

def make_json_response(json):
    return Response(json.encode('utf8'), 200, mimetype = 'application/json')

# By default, send out the standard client
@app.route('/')
def index():
    return render_template('index.haml')

@app.route('/challenges.html')
def challenges_web():
    return render_template('challenges.haml')

@app.route('/api/challenges')
def challenges_api():
    # This is a lot of parsing and unparsing of json...
    challenges = []
    for challenge in config.sections():
        meta = requests.get("http://%(host)s:%(port)s/meta" % {
                'host': config.get(challenge, 'host'),
                'port': config.get(challenge, 'port')}).json()
        stats = requests.get("http://%(host)s:%(port)s/stats" % {
                'host': config.get(challenge, 'host'),
                'port': config.get(challenge, 'port')}).json()

        meta.update(stats)
        pprint(meta)
        challenges.append(meta)
    return jsonify({'challenges': challenges})

@app.route('/api/task')
def task():
    # We need to find a task for the user to work on, based (as much
    # as possible)
    ## We may want to consider a service like
    ## http://www.maxmind.com/en/web_services#city for a fallback in the future
    #
    difficulty = request.args.get('difficulty', 'easy')
    print difficulty
    near = request.args.get('near')
    if near:
        lat, lon = near.split(',')
        point = shapely.geometry.Point(lat, lon)
    # Now we look for an appropriate task
    challenges = []
    for challenge in config.sections():
        if config.get(challenge, 'difficulty') == difficulty:
            print "Difficulty matches"
            if near:
                bbox_list = eval(config.get(challenge, 'bbox'))
                box = shapely.geometry.box(*bbox_list)
                if box.contains(point):
                    challenges.append(challenge)
            else:
                challenges.append(challenge)
    if challenges:
        return jsonify({'challenges': challenges})
    else:
        return "No matching challenges\n", 404
    
@app.route('/c/<challenge>/meta')
def challenge_meta(challenge):
    if config.has_section(challenge):
        return get_meta(challenge)
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/stats')
def challenge_stats(challenge):
    if config.has_section(challenge):
        return get_stats(challenge)
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/task')
def challenge_task(challenge):
    if config.has_section(challenge):
        return get_task(challenge, request.args.get('near'))
    else:
        return "No such challenge\n", 404

@app.route('/c/<challenge>/task/<id>', methods = ['POST'])
def challenge_post(challenge, task_id):
    if config.has_section(challenge):
        dct = request.form
        return post_task(challenge, task_id, dct)
    else:
        return "No such challenge\n", 404

@app.route('/<path:path>')
def catch_all(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(port=5000)
