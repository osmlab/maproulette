# The application secret key
SECRET_KEY = 'CHANGE THIS'

# The OAuth configuration paramters for OSM.
OSM = {
    'base_url': 'http://www.openstreetmap.org/api/0.6/',
    'request_token_url':
    'https://www.openstreetmap.org/oauth/request_token',
    'access_token_url': 'https://www.openstreetmap.org/oauth/access_token',
    'authorize_url': 'https://www.openstreetmap.org/oauth/authorize',
    'consumer_key': 'CHANGE THIS',
    'consumer_secret': 'CHANGE THIS'
}

# by default, disable Flask debug and testing modes
DEBUG = False  # Also remember to change LOGLEVEL below
TESTING = False

# This is the buffer for looking for tasks / challenges near the given
# lon/lat
NEARBUFFER = 0.01

# this is the threshold in square degrees
# for considering a challenge 'local'
MAX_SQ_DEGREES_FOR_LOCAL = 10

# The database connection
SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette"

# Logging details
import logging
LOGFILE = 'CHANGE THIS'
LOGLEVEL = logging.DEBUG

# the default challenge to run
DEFAULT_CHALLENGE = 'CHANGE THIS'

# show a teaser page instead of the real thing
TEASER = False
# the text that should go into the teaser
TEASER_TEXT = 'New MapRoulette Coming SOON!'

# IP Whitelist for external API calls
# (/api/admin/*, /api/stats*, /api/users, /api/challenges)
IP_WHITELIST = []

# Service API keys
MAILGUN_API_KEY = 'CHANGE THIS'
SKOBBLER_API_KEY = 'CHANGE THIS'

# URL to the metrics site instance, for allowing CORS requests from there
METRICS_URL = 'http://metrics.maproulette.org/'
