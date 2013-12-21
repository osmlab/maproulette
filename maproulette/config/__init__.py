import os

# Configuration classes


class Config(object):
    DEBUG = False
    TESTING = False

    # The application secret key
    SECRET_KEY = os.urandom(24)

    # This is the buffer for looking for tasks / challenges near the given
    # lon/lat
    NEARBUFFER = 0.01

    # The OAuth configuration paramters for OSM.
    # The example key and secret point to the MapRoulette application
    # registered at http://api06.dev.openstreetmap.org/api/0.6/
    # This cannot be used in production.
    OSM = {
        'base_url': 'http://api06.dev.openstreetmap.org/api/0.6/',
        'request_token_url':
        'http://api06.dev.openstreetmap.org/oauth/request_token',
        'access_token_url':
        'http://api06.dev.openstreetmap.org/oauth/access_token',
        'authorize_url': 'http://api06.dev.openstreetmap.org/oauth/authorize',
        'consumer_key': 'dFdzJzU4rMaemzZXdhCR8HOixu21fT9B726uyzU8',
        'consumer_secret': 'BhXKPNGDJHBVhkPfwyP5VPIHSDpSQXe63vwaTJ5l'
    }


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette"
    OSM = {
        'base_url': 'http://www.openstreetmap.org/api/0.6/',
        'request_token_url':
        'http://www.openstreetmap.org/oauth/request_token',
        'access_token_url': 'http://www.openstreetmap.org/oauth/access_token',
        'authorize_url': 'http://www.openstreetmap.org/oauth/authorize',
        'consumer_key': 'INSERT_CONSUMER_KEY_HERE',
        'consumer_secret': 'INSERT_CONSUMER_SECRET_HERE'
    }


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette_dev"
    #DEBUG = True


class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette_test"
    TESTING = True
