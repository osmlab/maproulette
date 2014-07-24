import os
from maproulette import app
from maproulette.models import db
import unittest
import tempfile


class MapRouletteTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_empty_db(self):
        r = self.app.get('/api/challenges')
        assert r.data.startswith('[]')


if __name__ == '__main__':
    unittest.main()
