import maproulette
import unittest
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

class MaprouletteTestCase(unittest.TestCase):

    def setUp(self):
        maproulette.app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://martijnv@localhost/maproulette_test'
        maproulette.app.config['TESTING'] = True
        self.app = maproulette.app.test_client()

    def tearDown(self):
        pass

    def test_alive(self):
        return_value = self.app.get('/api/ping')
        assert 'I am alive' in return_value.data

    def test_empty_challenge(self):
        '''assert that there are no challenges in the database'''
        return_value = self.app.get('/api/challenges')
        assert return_value.status_code == 200
        assert return_value.data[:2] == "[]"


if __name__ == '__main__':
    unittest.main()