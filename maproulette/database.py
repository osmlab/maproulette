from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
try:
    import settings
    settings_keys = dir(settings)
except ImportError:
    sys.stderr.write("""There must be a settings.py file""")
    sys.exit(2)


engine = create_engine(settings.db_connection, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import maproulette.models
    Base.metadata.create_all(bind=engine)
