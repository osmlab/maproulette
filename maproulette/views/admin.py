from flask import Flask, request
from flask.ext.restful import Resource, Api, fields, marshal_with
from maproulette import app
from maproulette.helpers import GeoPoint, JsonData
from maproulette.models import Challenge, Task, Action, db
from flask.helpers import localonly

challenge_fields = {'id': fields.String(attribute='slug'),
                    'title': fields.String,
                    'description': fields.String,
                    'blurb': fields.String,
                    'help': fields.String,
                    'instruction': fields.String,
                    'run': fields.String,
                    'active': fields.Boolean,
                    'difficulty': fields.Integer}

task_fields = {'id': fields.String(attribute='identifier'),
               'location': fields.String,
               'run': fields.String,
               'instruction': fields.String}


class AdminChallengeApi(Resource):
    method_decorators = [localonly]

    @marshal_with(challenge_fields)
    def get(self, challenge_slug):
        challenge = get_challenge_or_404(challenge_slug,
                                         instance_type=False,
                                         abort_if_inactive=False)
        return challenge

    def post(self, challenge_slug):
        challenge = get_challenge_or_404(challenge_slug,
                                         instance_type=False,
                                         abort_if_inactive=False)
        parser = reqparse.RequestParser()
        parser.add_argument('title')
        parser.add_argument('description')
        parser.add_argument('blurb')
        parser.add_argument('help')
        parser.add_argument('difficulty', type=int, choices=[1, 2, 3],
                            help="Could not parse difficulty")
        parser.add_argument('active', type=int, choices=[0, 1],
                            help="Could not parse active")
        args = parser.parse_args()
        if args['title']:
            challenge.title = args['title']
        if args['description']:
            challenge.description = args['description']
        if args['blurb']:
            challenge.blurb = args['blurb']
        if args['help']:
            challenge.help = args['help']


class AdminTasksApi(Resource):
    method_decorators = [localonly]

    def post(self, challenge_slug):
        challenge = get_challenge_or_404(challenge_slug,
                                         instance_type=False,
                                         abort_if_inactive=False)


class AdminTasksApi(Resource):
    method_decorators = [localonly]

    def post(self, challenge_slug):
        challenge = get_challenge_or_404(challenge_slug, instance_type=False,
                                         abort_if_inactive=False)
        parser = reqparse.RequestParser()
        parser.add_argument('run', required=True,
                            help="Bulk inserts require a Run ID")
        parser.add_argument('tasks', type=JsonTasks, required=True,
                            help="Bulk inserts require tasks")
        run = args['run']
        tasks = args['tasks'].data
        results = []
        for t in tasks:
            task = Task(challenge.slug, t['id'])
            task.instruction = t['text']
            task.location = t['location']
            task.manifest = t['manifest']
            task.run = run
            results.append(marshal(task), task_fields)
            db.session.add(task)
            db.session.flush()
            action = Action(task.id, "created")
            db.session.add(action)
            # This is going to be a bit challenge specific
            action = Action(task.id, "available")
            db.session.add(action)
        db.session.commit()
        return jsonify(tasks=results)


class AdminTaskApi(Resource):
    method_decorators = [localonly]

    @marshal_with(task_fields)
    def get(self, challenge_slug, task_id):
        challenge = get_challenge_or_404(challenge_slug, instance_type=False,
                                         abort_if_inactive=False)
        task = get_task_or_404(challenge, task_id)
        return task

    @marshal_with(task_fields)
    def put(self, challenge_slug, task_id):
        challenge = get_challenge_or_404(challenge_slug, instance_type=False,
                                         abort_if_inactive=False)
        task = Task.query(Task.identifier == task_id).\
            filter(Task.challenge_slug == challenge.slug).first()
        if task:
            action = Action(task.id, "modified")
            db.session.add(action)
        else:
            task = Task(challenge.slug, task_id)
            db.session.add(task)
            db.session.flush()
            action = Action(task.id, "created")
            db.session.add(action)
            action = Action(task.id, "available")
            db.session.add(action)
        parser = reqparse.RequestParser()
        parser.add_argument('run', required=True,
                            help="New tasks must include a Run ID")
        parser.add_argument('text', dest='instruction')
        parser.add_argument('location', type=GeoPoint,
                            help="Location must be in the form lon|lat")
        parser.add_argument('manifest', type=JsonData,
                            help="Manifest must be valid JSON")
        args = parser.parse_args()
        if request.form.get('run'):
            task['run'] = request.form['run']
        if request.form.get('text'):
            task['instruction'] = request.form['text']
        if request.form.get('location'):
            # WILL THIS WORK???
            task['location'] = request.form['location']
        if request.form.get('manifest'):
            task['manifest'] = request.form['manifest']
        # LET'S HOPE ADDING IT TWICE DOESN'T BREAK ANYTHING
        db.session.add(task)
        db.commit()
        return task

    @marshal_with(task_fields)
    def post(self, challenge_slug, task_id):
        challenge = get_challenge_or_404(challenge_slug, instance_type=False,
                                         abort_if_inactive=False)
        task = get_task_or_404(challenge, task_id)
        if request.form.get('run'):
            task['run'] = request.form['run']
        if request.form.get('text'):
            task['instruction'] = request.form['text']
        if request.form.get('location'):
            # WILL THIS WORK???
            task['location'] = request.form['location']
        if request.form.get('manifest'):
            task['manifest'] = request.form['manifest']
        db.session.add(task)
        db.commit()
        return task
