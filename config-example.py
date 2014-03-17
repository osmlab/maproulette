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
DEBUG = False
TESTING = False

# This is the buffer for looking for tasks / challenges near the given
# lon/lat
NEARBUFFER = 0.01

# this is the threshold in square degrees
# for considering a challenge 'local'
MAX_SQ_DEGREES_FOR_LOCAL = 10

from datetime import timedelta

# The expiration threshold for tasks that are 'assigned' or 'editing'
TASK_EXPIRATION_THRESHOLD = timedelta(hours=1)

# The time buffer between a task marked as fixed and the timestamp on the
# changeset in OSM. (Used in validation)
MAX_CHANGESET_OFFSET = timedelta(hours=1)

# The database connection
SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette"

# The application log file
LOGFILE = 'CHANGE THIS'

# the default challenge to run
DEFAULT_CHALLENGE = 'CHANGE THIS'

# show a teaser page instead of the real thing
TEASER = False
# the text that should go into the teaser
TEASER_TEXT = 'New MapRoulette Coming SOON!'
