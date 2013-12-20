# Set the path
import os, sys
import subprocess
from flask.ext.script import Manager, Server
from maproulette import app

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

manager = Manager(app)

# Turn on debugger by default and reloader
manager.add_command("runserver", Server(
    use_debugger = True,
    use_reloader = True,
    host = '0.0.0.0',
    port = 3000)
)

@manager.command
def clean_pyc():
    """Removes all *.pyc files from the project folder"""
    clean_command = "find . -name *.pyc -delete".split()
    subprocess.call(clean_command)

@manager.command
def drop_db():
    """Creates the database tables"""
    from maproulette import database
    database.drop_db()

@manager.command
def create_db():
    """Creates the database tables"""
    from maproulette import database
    database.init_db()

if __name__ == "__main__":
    manager.run()
