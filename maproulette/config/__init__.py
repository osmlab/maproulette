
# Configuration classes


class Config(object):
    """Base configuration class"""
    # by default, disable Flask debug and testing modes
    DEBUG = False
    TESTING = False

    # This is the buffer for looking for tasks / challenges near the given
    # lon/lat
    NEARBUFFER = 0.01

    # this is the threshold in square degrees
    # for considering a challenge 'local'
    MAX_SQ_DEGREES_FOR_LOCAL = 10

    DEFAULT_CHALLENGE = 'test1'


class ProductionConfig(Config):
    """Production configuration class"""

    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette"
    LOGFILE = '/srv/www/maproulette/log/flask/maproulette.log'


class DevelopmentConfig(Config):
    """Development configuration class"""
    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette_dev"
    DEBUG = True


class TestingConfig(Config):
    """Test configuration class"""
    SQLALCHEMY_DATABASE_URI = "postgresql://osm:osm@localhost/maproulette_test"
    TESTING = True
