import sys
import os
import logging

# The application secret key
SECRET_KEY = 'CHANGE THIS'

# The OAuth configuration paramters for OSM.
OSM = {
    'base_url': 'https://master.apis.dev.openstreetmap.org/api/0.6/',
    'request_token_url': 'https://master.apis.dev.openstreetmap.org/oauth/request_token',
    'access_token_url': 'https://master.apis.dev.openstreetmap.org/oauth/access_token',
    'authorize_url': 'https://master.apis.dev.openstreetmap.org/oauth/authorize',
    'consumer_key': 'CHANGE THIS',
    'consumer_secret': 'CHANGE_THIS'
}

# Set debugging mode. This is detected by looking at the 'runserver' argument passed to manage.py
DEBUG = (len(sys.argv)>1 and sys.argv[1] == 'runserver')

# This is the buffer for looking for tasks / challenges near the given
# lon/lat
NEARBUFFER = 0.01

# this is the threshold in square degrees
# for considering a challenge 'local'
MAX_SQ_DEGREES_FOR_LOCAL = 10

# The database connection
SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette"

# Logging details
LOGFILE = os.path.join(os.path.expanduser('~'), '/tmp/maproulette.log')
LOGLEVEL = logging.DEBUG if DEBUG else logging.INFO

# the default challenge to run
DEFAULT_CHALLENGE = 'CHANGE_THIS'

# IP Whitelist for external API calls
# (/api/admin/*, /api/stats*, /api/users, /api/challenges)
IP_WHITELIST = []

# Service API keys
MAILGUN_API_KEY = 'CHANGE THIS'

# URL to the metrics site instance, for allowing CORS requests from there
METRICS_URL = 'http://metrics.maproulette.org/'

# Max number of tasks in a bulk task update
MAX_TASKS_BULK_UPDATE = 5000

# Basic Authentication user / pass
AUTHORIZED_USER = 'testuser'
AUTHORIZED_PASSWORD = 'password'

# SQLAlchemy defaults
SQLALCHEMY_TRACK_MODIFICATIONS = False