from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource, abort
from flask.ext.restful.fields import Raw
from flask.ext.restful.utils import cors
from flask import session, request, url_for
from maproulette.helpers import get_random_task,\
    get_challenge_or_404, get_task_or_404,\
    require_signedin, osmerror, \
    json_to_task, geojson_to_task, refine_with_user_area, user_area_is_defined,\
    send_email, as_stats_dict, challenge_exists, requires_auth
from maproulette.models import Challenge, Task, Action, User, db
from geoalchemy2.functions import ST_Buffer
from geoalchemy2.shape import to_shape
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
import geojson
import json
import re

message_internal_server_error = 'Something really unexpected happened...'

class ProtectedResource(Resource):

    """A Resource that requires the caller to be authenticated against OSM"""
    method_decorators = [require_signedin]


class PointField(Raw):

    """An encoded point"""

    def format(self, geometry):
        return '%f|%f' % to_shape(geometry).coords[0]


# Marshal fields for the challenge list. #FIXME islocal is not used at the moment.
challenge_summary = {
    'slug': fields.String,
    'title': fields.String,
    'difficulty': fields.Integer,
    'description': fields.String,
    'help': fields.String,
    'blurb': fields.String,
    'islocal': fields.Boolean,
    'active': fields.Boolean
}

# Marshal fields for challenge detail. FIXME This should include the geometry as well
challenge_detail = {
    'slug': fields.String,
    'title': fields.String,
    'difficulty': fields.Integer,
    'description': fields.String,
    'instruction': fields.String,
    'help': fields.String,
    'blurb': fields.String,
    'active': fields.Boolean,
    'type': fields.String
}

task_fields = {
    'identifier': fields.String(attribute='identifier'),
    'instruction': fields.String(attribute='instruction'),
    'location': PointField,
    'status': fields.String
}

me_fields = {
    'username': fields.String(attribute='display_name'),
    'osm_id': fields.String,
    'lat': fields.Float,
    'lon': fields.Float,
    'radius': fields.Integer
}

action_fields = {
    'task': fields.String(attribute='task_id'),
    'timestamp': fields.DateTime,
    'status': fields.String,
    'user': fields.String(attribute='user_id')
}

user_summary = {
    'id': fields.Integer,
    'display_name': fields.String
}

api = Api(app)
api.decorators = [cors.crossdomain(origin=app.config['METRICS_URL'])]

# override the default JSON representation to support the geo objects


class ApiPing(Resource):

    """a simple ping endpoint"""

    def get(self):
        return ["I am alive"]


class ApiChallenge(ProtectedResource):

    @marshal_with(challenge_summary)
    def get(self):
        """Return a single challenge"""
        c = None
        # start with the default challenge
        c = Challenge.query.filter(Challenge.slug == app.config["DEFAULT_CHALLENGE"]).first()
        # if it exists and is active, return it:
        if c is not None and c.active:
            return c
        # else just get the first active one:
        c = Challenge.query.filter(Challenge.active).first()
        if c is not None:
            return c
        # if no active challenges exist, abort with a 404. This Should Never Happen.
        abort(404)


class ApiChallengeList(Resource):

    """Challenge list endpoint"""

    @marshal_with(challenge_summary)
    def get(self, **kwargs):
        """returns a list of challenges.
        Optional URL parameters are:
        difficulty: the desired difficulty to filter on
        (1=easy, 2=medium, 3=hard)
        lon/lat: the coordinate to filter on (returns only
        challenges whose bounding polygons contain this point)
        example: /api/challenges?lon=-100.22&lat=40.45&difficulty=2
        """

        # initialize the parser
        parser = reqparse.RequestParser()
        # FIXME this should be a bool but that does not seem to work.
        parser.add_argument('difficulty',
                            type=int, choices=[1, 2, 3],
                            help='difficulty is not 1, 2, 3')
        parser.add_argument('lon',
                            type=float,
                            help="lon is not a float")
        parser.add_argument('lat',
                            type=float,
                            help="lat is not a float")
        parser.add_argument('radius',
                            type=int,
                            help="radius is not an int")
        args = parser.parse_args()

        difficulty = None

        # Try to get difficulty from argument, or users preference
        difficulty = args.get('difficulty')
        lon = args.get('lon')
        lat = args.get('lat')
        radius = args.get('radius')

        # get the list of challenges meeting the criteria
        query = db.session.query(Challenge)

        if difficulty is not None:
            query = query.filter_by(difficulty=difficulty)
        if (lon is not None and lat is not None and radius is not None):
            print "got lon, lat, rad: {lon}, {lat}, {rad}".format(lon=lon, lat=lat, rad=radius)
            query = query.filter(
                Challenge.polygon.ST_Contains(
                    ST_Buffer('POINT({lon} {lat})'.format(lon=lon, lat=lat),
                              radius)))

        challenges = query.all()

        return challenges


class ApiChallengeDetail(Resource):

    """Single Challenge endpoint"""

    def get(self, slug):
        """Return a single challenge by slug"""
        challenge = get_challenge_or_404(slug, abort_if_inactive=False)
        return marshal(challenge, challenge_detail)


class ApiSelfInfo(ProtectedResource):

    """Information about the currently logged in user"""

    def get(self):
        """Return information about the logged in user"""
        return marshal(session, me_fields)

    def put(self):
        """User setting information about themselves"""
        payload = None
        try:
            payload = json.loads(request.data)
        except Exception:
            abort(400, message="JSON bad")
        [session.pop(k, None) for k, v in payload.iteritems() if v is None]
        for k, v in payload.iteritems():
            if k not in me_fields.keys():
                abort(400, message='you cannot set this key')
            if v is not None:
                app.logger.debug('setting {k} to {v}'.format(k=k, v=v))
                session[k] = v
        return {}, 200


class ApiChallengePolygon(ProtectedResource):

    """Challenge geometry endpoint"""

    def get(self, slug):
        """Return the geometry (spatial extent)
        for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return challenge.polygon


class ApiChallengeSummaryStats(Resource):

    """Challenge Statistics endpoint"""

    def get(self, challenge_slug):
        """Return statistics for the challenge identified by 'slug'"""
        # get the challenge
        challenge = get_challenge_or_404(challenge_slug, abort_if_inactive=False)

        # query the number of tasks
        query = db.session.query(Task).filter_by(challenge_slug=challenge.slug)
        # refine with the user defined editing area
        query = refine_with_user_area(query)
        # emit count
        total = query.count()

        # get the approximate number of available tasks
        unfixed = query.filter(Task.status.in_(
            ['available', 'created', 'skipped'])).count()

        return {'total': total, 'unfixed': unfixed}


class ApiStats(Resource):

    """Statistics Endpoint"""

    def get(self, challenge_slug=None, user_id=None):
        from dateutil import parser as dateparser
        from datetime import datetime
        from maproulette.models import AggregateMetrics

        start = None
        end = None

        parser = reqparse.RequestParser()
        parser.add_argument('start', type=str,
                            help='start datetime yyyymmddhhmm')
        parser.add_argument('end', type=str,
                            help='end datetime yyyymmddhhmm')

        args = parser.parse_args()

        breakdown = False

        select_fields = [
            AggregateMetrics.status,
            func.sum(AggregateMetrics.count)]

        group_fields = [
            AggregateMetrics.status]

        if request.path.endswith('/users'):
            select_fields.insert(0, AggregateMetrics.user_name)
            group_fields.insert(0, AggregateMetrics.user_name)
            breakdown = True
        elif request.path.endswith('/challenges'):
            select_fields.insert(0, AggregateMetrics.challenge_slug)
            group_fields.insert(0, AggregateMetrics.challenge_slug)
            breakdown = True

        stats_query = db.session.query(
            *select_fields).group_by(
            *group_fields)

        # stats for a specific challenge
        if challenge_slug is not None:
            stats_query = stats_query.filter_by(
                challenge_slug=challenge_slug)

        # stats for a specific user
        if user_id is not None:
            stats_query = stats_query.filter_by(
                user_id=user_id)

        # time slicing filters
        if args['start'] is not None:
            start = dateparser.parse(args['start'])
            if args['end'] is None:
                end = datetime.utcnow()
            else:
                end = dateparser.parse(args['end'])
            stats_query = stats_query.filter(
                AggregateMetrics.timestamp.between(start, end))

        if breakdown:
            # if this is a breakdown by a secondary variable, the
            # query will have returned three columns and we need to
            # build a nested dictionary.
            return as_stats_dict(stats_query.all(), start=start, end=end)
        else:
            return dict(stats_query.all())


class ApiStatsHistory(Resource):

    """Day to day history overall"""

    def get(self, challenge_slug=None, user_id=None):

        from maproulette.models import HistoricalMetrics as HM

        start = None
        end = None

        from dateutil import parser as dateparser
        from datetime import datetime
        parser = reqparse.RequestParser()
        parser.add_argument('start', type=str,
                            help='start datetime yyyymmddhhmm')
        parser.add_argument('end', type=str,
                            help='end datetime yyyymmddhhmm')

        args = parser.parse_args()

        stats_query = db.session.query(
            HM.timestamp,
            HM.status,
            func.sum(HM.count))

        if challenge_slug is not None:
            stats_query = stats_query.filter(HM.challenge_slug == challenge_slug)
        if user_id is not None:
            stats_query = stats_query.filter(HM.user_id == user_id)

        stats_query = stats_query.group_by(
            HM.timestamp, HM.status).order_by(
            HM.status)

        # time slicing filters
        if args['start'] is not None:
            start = dateparser.parse(args['start'])
            if args['end'] is None:
                end = datetime.utcnow()
            else:
                end = dateparser.parse(args['end'])
            stats_query = stats_query.filter(
                Action.timestamp.between(start, end))

        return as_stats_dict(
            stats_query.all(),
            order=[1, 0, 2],
            start=start,
            end=end)


class ApiChallengeTask(ProtectedResource):

    """Random Task endpoint"""

    def get(self, slug):
        """Returns a task for specified challenge"""
        challenge = get_challenge_or_404(slug, True)
        parser = reqparse.RequestParser()
        parser.add_argument('lon', type=float,
                            help='longitude could not be parsed')
        parser.add_argument('lat', type=float,
                            help='longitude could not be parsed')
        parser.add_argument('assign', type=int, default=1,
                            help='Assign could not be parsed')
        args = parser.parse_args()
        osmid = session.get('osm_id')
        assign = args['assign']
        lon = args['lon']
        lat = args['lat']

        task = None
        if lon and lat:
            coordWKT = 'POINT(%s %s)' % (lat, lon)
            task = Task.query.filter(Task.location.ST_Intersects(
                ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).first()
        if task is None:  # we did not get a lon/lat or there was no task close
            # If no location is specified, or no tasks were found, gather
            # random tasks
            task = get_random_task(challenge)
            # If no tasks are found with this method, then this challenge
            # is complete
        if task is None:
            if not user_area_is_defined():
                # send email and deactivate challenge only when
                # there are no more tasks for the entire challenge,
                # not if the user has defined an area to work on.
                subject = "Challenge {} is complete".format(challenge.slug)
                body = "{challenge} has no remaining tasks"
                " on server {server}".format(
                    challenge=challenge.title,
                    server=url_for('index', _external=True))
                send_email("maproulette@maproulette.org", subject, body)

                # Deactivate the challenge
                challenge.active = False
                merged_c = db.session.merge(challenge)
                db.session.add(merged_c)
                db.session.commit()

            # Is this the right error?
            return osmerror("ChallengeComplete",
                            "Challenge {} is complete".format(challenge.title))
        if assign:
            task.append_action(Action("assigned", osmid))
            merged_t = db.session.merge(task)
            db.session.add(merged_t)

        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='The session and the database did not agree for task identifier {identifier}: {message}'.format(id=task.identifier, message=e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return marshal(task, task_fields)


class ApiChallengeTaskDetails(ProtectedResource):

    """Task details endpoint"""

    def get(self, slug, identifier):
        """Returns non-geo details for the task identified by
        'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return marshal(task, task_fields)

    def put(self, slug, identifier):
        """Update the task identified by 'identifier' from
        the challenge identified by 'slug'"""
        # initialize the parser
        parser = reqparse.RequestParser()
        parser.add_argument('action', type=str,
                            help='action cannot be parsed')
        parser.add_argument('editor', type=str,
                            help="editor cannot be parsed")
        args = parser.parse_args()

        # get the task
        task = get_task_or_404(slug, identifier)
        # append the latest action to it.
        task.append_action(Action(args.action,
                                  session.get('osm_id'),
                                  args.editor))
        merged_t = db.session.merge(task)
        db.session.add(merged_t)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='The session and the database did not agree for task identifier {identifier}: {message}'.format(id=task.identifier, message=e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 200


class ApiChallengeTaskStatus(ProtectedResource):

    """Task status endpoint"""

    def get(self, slug, identifier):
        """Returns current status for the task identified by
        'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return {'status': task.status}


class ApiChallengeTaskGeometries(ProtectedResource):

    """Task geometry endpoint"""

    def get(self, slug, identifier):
        """Returns the geometries for the task identified by
        'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        geometries = [geojson.Feature(
            geometry=g.geometry,
            properties={
                'selected': True,
                'osmid': g.osmid}) for g in task.geometries]
        return geojson.FeatureCollection(geometries)


class ApiUsers(Resource):

    """Users list endpont"""

    @marshal_with(user_summary)
    def get(self):
        """Returns a list of users"""
        users = db.session.query(User).all()
        return users

# Add all resources to the RESTful API
api.add_resource(ApiPing,
                 '/api/ping')
api.add_resource(ApiSelfInfo,
                 '/api/me')
# statistics endpoint
api.add_resource(ApiStats,
                 '/api/stats',
                 '/api/stats/users',
                 '/api/stats/challenges',
                 '/api/stats/challenge/<string:challenge_slug>',
                 '/api/stats/challenge/<string:challenge_slug>/users',
                 '/api/stats/user/<int:user_id>',
                 '/api/stats/user/<int:user_id>/challenges')
api.add_resource(ApiStatsHistory,
                 '/api/stats/history',
                 '/api/stats/challenge/<string:challenge_slug>/history',
                 '/api/stats/challenge/<string:challenge_slug>/user/<string:user_id>/history',
                 '/api/stats/user/<int:user_id>/history',
                 '/api/stats/user/<int:user_id>/challenge/<string:challenge_slug>/history')
api.add_resource(ApiChallengeSummaryStats,
                 '/api/challenge/<string:challenge_slug>/summary')
# task endpoints
api.add_resource(ApiChallengeTask,
                 '/api/challenge/<slug>/task')
api.add_resource(ApiChallengeTaskDetails,
                 '/api/challenge/<slug>/task/<identifier>')
api.add_resource(ApiChallengeTaskGeometries,
                 '/api/challenge/<slug>/task/<identifier>/geometries')
api.add_resource(ApiChallengeTaskStatus,
                 '/api/challenge/<slug>/task/<identifier>/status')
# challenge endpoints
api.add_resource(ApiChallengeList,
                 '/api/challenges')
api.add_resource(ApiChallenge,
                 '/api/challenge')
api.add_resource(ApiChallengeDetail,
                 '/api/challenge/<string:slug>')
api.add_resource(ApiChallengePolygon,
                 '/api/challenge/<string:slug>/polygon')
# users list
api.add_resource(ApiUsers,
                 '/api/users')


#
# The Admin API ################
#


class AdminApiChallenge(Resource):

    """Admin challenge creation endpoint"""

    @requires_auth
    def post(self, slug):
        payload = None
        if challenge_exists(slug):
            app.logger.debug('The challenge already exists')
            abort(409, message='This challenge already exists.')
        if not re.match("^[\w\d_-]+$", slug):
            app.logger.debug('The challenge slug should contain only a-z, A-Z, 0-9, _, -')
            abort(400, message='The challenge slug should contain only a-z, A-Z, 0-9, _, -')
        try:
            payload = json.loads(request.data)
        except Exception as e:
            app.logger.debug('POST request does not have a JSON payload')
            app.logger.debug(request.data)
            abort(400, message=e.message)
        if 'title' not in payload:
            app.logger.debug('A new challenge must have title')
            abort(400, message="A new challenge must have title")
        c = Challenge(slug, payload.get('title'))
        if 'title' in payload:
            c.title = payload.get('title')
        if 'geometry' in payload:
            c.geometry = payload.get('geometry')
        if 'description' in payload:
            c.description = payload.get('description')
        if 'blurb' in payload:
            c.blurb = payload.get('blurb')
        if 'help' in payload:
            c.help = payload.get('help')
        if 'instruction' in payload:
            c.instruction = payload.get('instruction')
        if 'active' in payload:
            c.active = payload.get('active')
        if 'difficulty' in payload:
            c.difficulty = payload.get('difficulty')
        db.session.add(c)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='The session and the database did not agree for challenge {slug}: {message}'.format(slug=challenge.slug, message=e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 201

    @requires_auth
    def put(self, slug):
        c = get_challenge_or_404(slug, abort_if_inactive=False)
        if not re.match("^[\w\d_-]+$", slug):
            abort(400, message='slug should contain only a-z, A-Z, 0-9, _, -')
        try:
            payload = json.loads(request.data)
        except Exception:
            abort(400, message="There is something wrong with your JSON.")
        if 'title' in payload:
            c.title = payload.get('title')
        if 'geometry' in payload:
            c.geometry = payload.get('geometry')
        if 'description' in payload:
            c.description = payload.get('description')
        if 'blurb' in payload:
            c.blurb = payload.get('blurb')
        if 'help' in payload:
            c.help = payload.get('help')
        if 'instruction' in payload:
            c.instruction = payload.get('instruction')
        if 'active' in payload:
            c.active = payload.get('active')
        if 'difficulty' in payload:
            c.difficulty = payload.get('difficulty')
        db.session.add(c)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='the session and the database did not agree: {}'.format(e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 200

    @requires_auth
    def delete(self, slug):
        """delete a challenge"""
        challenge = get_challenge_or_404(slug, abort_if_inactive=False)
        db.session.delete(challenge)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='the session and the database did not agree: {}'.format(e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message='Something really unexpected happened...')
        return {}, 204


class AdminApiTaskStatuses(Resource):

    """Admin Task status endpoint"""

    @requires_auth
    def get(self, slug):
        """Return task statuses for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True, False)
        return [{
            'identifier': task.identifier,
            'status': task.status} for task in challenge.tasks]


class AdminApiUpdateTask(Resource):

    """Challenge Task Create / Update endpoint"""

    @requires_auth
    def post(self, slug, identifier):
        """create one task."""

        if not re.match("^[\w\d_-]+$", identifier):
            abort(400, message='identifier should contain only a-z, A-Z, 0-9, _, -')

        # Parse the posted data
        try:
            app.logger.debug(request.data)
            t = json_to_task(
                slug,
                json.loads(request.data),
                identifier=identifier)
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='You posted a task ({identifier}) that already existed: {message}'.format(identifier=t.identifier, message=e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 201

    @requires_auth
    def put(self, slug, identifier):
        """update one task."""

        # Parse the posted data
        t = json_to_task(
            slug,
            json.loads(request.data),
            task=get_task_or_404(slug, identifier))
        db.session.add(t)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='The session and the database did not agree: {}'.format(e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message='something unexpected happened')
        return {}, 200

    @requires_auth
    def delete(self, slug, identifier):
        """Delete a task"""

        t = get_task_or_404(slug, identifier)
        t.append_action(Action('deleted'))
        merged_t = db.session.merge(t)
        db.session.add(merged_t)
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='the session and the database did not agree: {}'.format(e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 204


class AdminApiUpdateTasksFromGeoJSON(Resource):

    """Bulk task create / update from GeoJSON endpoint"""

    @requires_auth
    def post(self, slug):
        """bulk create tasks"""

        app.logger.debug('we expect geojson')
        data = json.loads(request.data)
        # if there are no features, bail
        app.logger.debug(data)
        if not isinstance(data, dict):
            abort(400, message='We need a dictionary')
        if not 'features' in data:
            abort(400, message='no features in geoJSON')
        # if there are too many features, bail
        if len(data['features']) > app.config['MAX_TASKS_BULK_UPDATE']:
            abort(400, message='more than the max number of allowed tasks ({})in bulk create'.format(app.config['MAX_TASKS_BULK_UPDATE']))
        # create tasks from each feature
        for feature in data['features']:
            task = geojson_to_task(slug, feature)
            if task is not None:
                db.session.add(task)
        # commit the tasks
        db.session.commit()
        return {}, 200

    @requires_auth
    def put(self, slug):
        """bulk update tasks"""

        app.logger.debug('we expect geojson')
        data = json.loads(request.data)
        # if there are no features, bail
        app.logger.debug(data)
        if not isinstance(data, dict):
            abort(400, )
        if not data['features']:
            abort(400, message='no features in geoJSON')
        # if there are too many features, bail
        if len(data['features']) > app.config['MAX_TASKS_BULK_UPDATE']:
            abort(400, message='more than the max number of allowed tasks ({})in bulk create'.format(app.config['MAX_TASKS_BULK_UPDATE']))
        # create tasks from each feature
        for feature in data['features']:
            task = geojson_to_task(slug, feature)
            if task is not None:
                db.session.add(task)
        # commit the tasks
        db.session.commit()
        return {}, 200


class AdminApiUpdateTasks(Resource):

    """Bulk task create / update endpoint"""

    @requires_auth
    def post(self, slug):
        """bulk create tasks"""

        # Get the posted data
        data = json.loads(request.data)
        app.logger.debug(len(data))
        app.logger.debug(app.config['MAX_TASKS_BULK_UPDATE'])

        if len(data) > app.config['MAX_TASKS_BULK_UPDATE']:
            abort(400, message='more than the max number of allowed tasks ({})in bulk create'.format(app.config['MAX_TASKS_BULK_UPDATE']))

        # debug output number of tasks being posted
        app.logger.debug('posting {number} tasks...'.format(number=len(data)))

        try:
            for task in data:
                if not 'identifier' in task:
                    abort(400, message='task must have identifier')
                if not re.match("^[\w\d_-]+$", task['identifier']):
                    abort(400, message='identifier should contain only a-z, A-Z, 0-9, _, -')
                if not 'geometries' in task:
                    abort(400, message='new task must have geometries')
                t = json_to_task(slug, task)
                db.session.add(t)

            # commit all dirty tasks at once.
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='You tried to post a task ({identifier}) that already existed: {message}'.format(identifier=task.identifier, message=e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 201

    @requires_auth
    def put(self, slug):

        """bulk update"""

        # Get the data
        data = json.loads(request.data)

        # debug output number of tasks being put
        app.logger.debug('putting {number} tasks...'.format(number=len(data)))

        if len(data) > app.config['MAX_TASKS_BULK_UPDATE']:
            abort(400, message='more than 5000 tasks in bulk update')

        for task in data:
            if not 'identifier' in task:
                abort(400, message='task must have identifier')
            if not isinstance(task['identifier'], basestring):
                abort(400, message='task identifier must be string')
            if not re.match("^[\w\d_-]+$", task['identifier']):
                abort(400, message='identifier should contain only a-z, A-Z, 0-9, _, -')
            t = json_to_task(slug,
                             task,
                             task=get_task_or_404(slug, task['identifier']))
            db.session.add(t)

        # commit all dirty tasks at once.
        try:
            db.session.commit()
        except Exception as e:
            if type(e) == IntegrityError:
                app.logger.warn(e.message)
                db.session.rollback()
                abort(409, message='the session and the database did not agree: {}'.format(e.message))
            else:
                app.logger.warn(e.message)
                abort(500, message=message_internal_server_error)
        return {}, 200

api.add_resource(AdminApiChallenge,
                 '/api/admin/challenge/<string:slug>')
api.add_resource(AdminApiTaskStatuses,
                 '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTasks,
                 '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTasksFromGeoJSON,
                 '/api/admin/challenge/<string:slug>/tasksfromgeojson')
api.add_resource(AdminApiUpdateTask,
                 '/api/admin/challenge/<string:slug>/task/<string:identifier>')
