import os
import maproulette
import unittest
import tempfile


class MapRouletteTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, maproulette.app.config['DATABASE'] = tempfile.mkstemp()
        maproulette.app.config['TESTING'] = True
        self.app = maproulette.app.test_client()
        maproulette.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(maproulette.app.config['DATABASE'])

if __name__ == '__main__':
    unittest.main()
