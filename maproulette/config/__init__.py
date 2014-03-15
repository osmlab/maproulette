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

    # show a teaser page instead of the real thing
    TEASER = False
    # the text that should go into the teaser
    TEASER_TEXT = 'New MapRoulette Coming SOON!'

    from datetime import timedelta

    # The expiration threshold for tasks that are 'assigned' or 'editing'
    TASK_EXPIRATION_THRESHOLD = timedelta(hours=1)

    # The time buffer between a task marked as fixed and the timestamp on the
    # changeset in OSM. (Used in validation)
    MAX_CHANGESET_OFFSET = timedelta(hours=1)


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
