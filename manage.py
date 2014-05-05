  # !/usr/bin/env python

import os
import sys
import subprocess
from flask.ext.runner import Manager
from maproulette import app
from maproulette.models import db
from flask.ext.migrate import MigrateCommand, Migrate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

migrate = Migrate(app, db)

manager = Manager(app)

manager.add_command('db', MigrateCommand)


@manager.command
def clean_pyc():
    """Removes all *.pyc files from the project folder"""
    clean_command = "find . -name *.pyc -delete".split()
    subprocess.call(clean_command)


@manager.command
def drop_db():
    """Creates the database tables"""
    db.drop_all()


@manager.command
def create_db():
    """Creates the database tables"""
    db.create_all()


@manager.command
def create_testdata(challenges=10, tasks=100):
    """Creates test data in the database"""
    import uuid
    import random
    from maproulette.models import db, Challenge, Task, TaskGeometry, Action
    from shapely.geometry import Point, LineString, box
    # the gettysburg address
    challenge_help_test = "Sample challenge *help* text"
    challenge_instruction_test = "Challenge instruction text"
    task_instruction_text = "Task instruction text"
    # delete old tasks and challenges
    db.session.query(TaskGeometry).delete()
    db.session.query(Action).delete()
    db.session.query(Task).delete()
    db.session.query(Challenge).delete()
    db.session.commit()
    for i in range(1, int(challenges) + 1):
        print "Generating Test Challenge #%d" % i
        minx = -120
        maxx = -40
        miny = 20
        maxy = 50
        challengepoly = None
        slug = "test%d" % i
        title = "Test Challenge %d" % i
        challenge = Challenge(slug, title)
        challenge.difficulty = random.choice([1, 2, 3])
        challenge.active = True
        challenge.blurb = "This is test challenge number %d" % i
        challenge.description = "This describes challenge %d in detail" % i
        challenge.help = challenge_help_test
        challenge.instruction = challenge_instruction_test
        # have bounding boxes for all but the first two challenges.
        if i > 2:
            minx = random.randrange(-120, -40)
            miny = random.randrange(20, 50)
            maxx = minx + 1
            maxy = miny + 1
            challengepoly = box(minx, miny, maxx, maxy)
            print "\tChallenge has a bounding box of ", challengepoly
            challenge.polygon = challengepoly
        db.session.add(challenge)

        # add some tasks to the challenge
        print "\tGenerating %i tasks for challenge %i" % (int(tasks), i)
        # generate NUM_TASKS random tasks
        for j in range(int(tasks)):
            # generate a unique identifier
            identifier = str(uuid.uuid4())
            # instantiate the task and register it with challenge 'test'
            # Initialize a task with its challenge slug and persistent ID
            task = Task(challenge.slug, identifier)
            # create two random points not too far apart
            p1 = Point(
                random.randrange(minx, maxx) + random.random(),
                random.randrange(miny, maxy) + random.random())
            p2 = Point(
                p1.x + (random.random() * random.choice((1, -1)) * 0.01),
                p1.y + (random.random() * random.choice((1, -1)) * 0.01))
            # create a linestring connecting the two points
            # no constructor for linestring from points?
            l1 = LineString([(p1.x, p1.y), (p2.x, p2.y)])
            # generate some random 'osm ids'
            osmids = [random.randrange(1000000, 1000000000) for _ in range(2)]
            # add the first point and the linestring to the task's geometries
            task.geometries.append(TaskGeometry(osmids[0], p1))
            task.geometries.append(TaskGeometry(osmids[1], l1))
            # because we are not using the API, we need to call set_location
            # explicitly to set the task's location
            task.set_location()
            # generate random string for the instruction
            task.instruction = task_instruction_text
            # add the task to the session
            db.session.add(task)

    # commit the generated tasks and the challenge to the database.
    db.session.commit()


@manager.command
def clean_stale_tasks():

    from maproulette.models import db, Task, Action
    from sqlalchemy.sql.functions import max
    from datetime import datetime, timedelta
    import pytz

    current_time = datetime.now(pytz.utc)
    stale_threshold = current_time - timedelta(hours=1)
    counter = 0

    for task in db.session.query(Task).filter(
        Task.status.in_(['assigned', 'editing'])).join(
        Task.actions).group_by(
            Task.id).having(max(Action.timestamp) < stale_threshold).all():
        task.append_action(Action("available"))
        db.session.add(task)
        print "setting task %s to available" % (task.identifier)
        counter += 1
    db.session.commit()
    print 'done. %i tasks made available' % counter


@manager.command
def populate_task_location():
    """This command populates the new location field for each task"""
    counter = 0
    from maproulette.models import db, Task
    for task in db.session.query(Task):
        task.set_location()
        counter += 1
    db.session.commit()
    print 'done. Location for %i tasks set' % counter


if __name__ == "__main__":
    manager.run()
