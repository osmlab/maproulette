#!/usr/bin/env python

# Simple server to fake maproulette server response.
# You need to have the bottle and cherrypy packages to run this.
#
# Then start it with:
# python server.py

from bottle import route
from bottle import put
from bottle import run
from bottle import request
import random
import sys
import time


@route('/')
def hello():
    return "<h1>Hello World!</h1>"


@put('/api/admin/challenge/<slug>/task/<identifier>')
def task(slug, identifier):
    payload = request.forms.keys()[0]

    nsec = 1
    text = "OK: {slug} {identifier}".format(slug=slug, identifier=identifier)

    print text, '...'
    sys.stdout.flush()

    time.sleep(nsec)

    print 'slept for {} seconds'.format(nsec)
    return {'slug': slug, 'identifier': identifier, 'random': random.random()}

if __name__ == '__main__':

    #run(host='0.0.0.0', port=5000)
    run(host='0.0.0.0', port=5000, server='cherrypy')
