from flask.ext.testing import TestCase
from maproulette import app, db


class MyTest(TestCase):

    SQLALCHEMY_DATABASE_URI = "postgresql://martijnv@localhost/maproulette_test"
    TESTING = True

    def create_app(self):
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_api_alive(self):
        response = self.client.get('/api/ping')
        assert 'I am alive' in response.data
