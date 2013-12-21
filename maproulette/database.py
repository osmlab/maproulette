from maproulette.models import db


def drop_db():
    db.drop_all()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from maproulette import models
    db.create_all()
