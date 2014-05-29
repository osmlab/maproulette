from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource
from flask.ext.restful.fields import Raw
from flask import session, request, abort, url_for
from maproulette.helpers import get_random_task,\
    get_challenge_or_404, get_task_or_404,\
    require_signedin, osmerror, challenge_exists,\
    parse_task_json, refine_with_user_area, user_area_is_defined,\
    send_email, dict_from_tuples
from maproulette.models import Challenge, Task, Action, User, db
from geoalchemy2.functions import ST_Buffer
from geoalchemy2.shape import to_shape
from sqlalchemy import func
import geojson
import json
import markdown


class ProtectedResource(Resource):

    """A Resource that requires the caller to be authenticated against OSM"""
    method_decorators = [require_signedin]


class PointField(Raw):

    """An encoded point"""

    def format(self, geometry):
        return '%f|%f' % to_shape(geometry).coords[0]


class MarkdownField(Raw):

    """Markdown text"""

    def format(self, text):
        return markdown.markdown(text)

challenge_summary = {
    'slug': fields.String,
    'title': fields.String,
    'difficulty': fields.Integer,
    'description': fields.String,
    'help': MarkdownField,
    'blurb': fields.String,
    'islocal': fields.Boolean
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

api = Api(app)

# override the default JSON representation to support the geo objects


class ApiPing(Resource):

    """a simple ping endpoint"""

    def get(self):
        return ["I am alive"]


class ApiGetAChallenge(ProtectedResource):

    @marshal_with(challenge_summary)
    def get(self):
        """Return a single challenge"""
        return get_challenge_or_404(app.config["DEFAULT_CHALLENGE"])


class ApiChallengeList(ProtectedResource):

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
        parser.add_argument('difficulty', type=int, choices=["1", "2", "3"],
                            help='difficulty is not 1, 2, 3')
        parser.add_argument('lon', type=float,
                            help="lon is not a float")
        parser.add_argument('lat', type=float,
                            help="lat is not a float")
        parser.add_argument('radius', type=int,
                            help="radius is not an int")
        parser.add_argument('include_inactive', type=bool, default=False,
                            help="include_inactive it not bool")
        args = parser.parse_args()

        difficulty = None
        contains = None

        # Try to get difficulty from argument, or users preference
        difficulty = args['difficulty']

        # get the list of challenges meeting the criteria
        query = db.session.query(Challenge)

        if not args.include_inactive:
            query = query.filter_by(active=True)

        if difficulty is not None:
            query = query.filter_by(difficulty=difficulty)
        if contains is not None:
            query = query.filter(Challenge.polygon.ST_Contains(contains))

        challenges = query.all()

        return challenges


class ApiChallengeDetail(ProtectedResource):

    """Single Challenge endpoint"""

    def get(self, slug):
        """Return a single challenge by slug"""
        challenge = get_challenge_or_404(slug, True)
        return marshal(challenge, challenge.marshal_fields)


class ApiSelfInfo(ProtectedResource):

    """Information about the currently logged in user"""

    def get(self):
        """Return information about the logged in user"""
        return marshal(session, me_fields)

    def put(self):
        """User setting information about themselves"""
        try:
            payload = json.loads(request.data)
        except Exception:
            abort(400)
        [session.pop(k, None) for k, v in payload.iteritems() if v is None]
        for k, v in payload.iteritems():
            if v is not None:
                session[k] = v
        return {}


class ApiChallengePolygon(ProtectedResource):

    """Challenge geometry endpoint"""

    def get(self, slug):
        """Return the geometry (spatial extent)
        for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return challenge.polygon


class ApiChallengeSummaryStats(ProtectedResource):

    """Challenge Statistics endpoint"""

    def get(self, challenge_slug):
        """Return statistics for the challenge identified by 'slug'"""
        # get the challenge
        challenge = get_challenge_or_404(challenge_slug, True)

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


class ApiStats(ProtectedResource):

    """Statistics Endpoint"""

    def get(self, challenge_slug=None, user_id=None):
        from dateutil import parser as dateparser
        from datetime import datetime
        parser = reqparse.RequestParser()
        parser.add_argument('start', type=str,
                            help='start datetime yyyymmddhhmm')
        parser.add_argument('end', type=str,
                            help='end datetime yyyymmddhhmm')

        args = parser.parse_args()
        breakdown = None

        # base CTE and query
        # the base CTE gets the set of latest actions for any task
        latest_cte = db.session.query(
            Action.id,
            Action.task_id,
            Action.timestamp,
            Action.user_id,
            Action.status,
            Task.challenge_slug,
            User.display_name).join(
            Task).outerjoin(User).distinct(
            Action.task_id).order_by(
            Action.task_id.desc()).cte(name='latest')

        # the base query gets a count on the base CTE grouped by status,
        # optionally broken down by users
        if request.path.endswith('/users'):
            breakdown = 'users'
            stats_query = db.session.query(
                latest_cte.c.display_name,
                latest_cte.c.status,
                func.count(latest_cte.c.id)).group_by(
                latest_cte.c.status,
                latest_cte.c.display_name)
        elif request.path.endswith('/challenges'):
            breakdown = 'challenges'
            stats_query = db.session.query(
                latest_cte.c.challenge_slug,
                latest_cte.c.status,
                func.count(latest_cte.c.id)).group_by(
                latest_cte.c.status,
                latest_cte.c.challenge_slug)
        else:
            stats_query = db.session.query(
                latest_cte.c.status,
                func.count(latest_cte.c.id)).group_by(
                latest_cte.c.status)

        # stats for a specific challenge
        if challenge_slug is not None:
            stats_query = stats_query.filter(
                latest_cte.c.challenge_slug == challenge_slug)

        # stats for a specific user
        if user_id is not None:
            stats_query = stats_query.filter(
                latest_cte.c.user_id == user_id)

        # time slicing filters
        if args['start'] is not None:
            start = dateparser.parse(args['start'])
            if args['end'] is None:
                end = datetime.utcnow()
            else:
                end = dateparser.parse(args['end'])
            stats_query = stats_query.filter(
                latest_cte.c.timestamp.between(start, end))

        if breakdown is not None:
            # if this is a breakdown by a secondary variable, the
            # query will have returned three columns and we need to
            # build a nested dictionary.
            return dict_from_tuples(stats_query.all())
        else:
            return dict(stats_query.all())


class ApiStatsHistory(ProtectedResource):

    """Day to day history overall"""

    def get(self):
        history_stats_query = db.session.query(
            func.date_trunc('day', Action.timestamp).label('day'),
            Action.status,
            func.count(Action.id)).group_by(
            'day', Action.status)
        return dict_from_tuples(history_stats_query.all())


class ApiStatsChallengeHistory(ProtectedResource):

    """Day to day history for a challenge"""

    def get(self, challenge_slug):
        challenge_history_stats_query = db.session.query(
            func.date_trunc('day', Action.timestamp).label('day'),
            Action.status,
            func.count(Action.id)).join(Task).filter_by(
            challenge_slug=challenge_slug).group_by(
            'day', Action.status)
        return dict_from_tuples(challenge_history_stats_query.all())


class ApiStatsUserHistory(ProtectedResource):

    """Day to day history for a user"""

    def get(self, user_id):
        user_history_stats_query = db.session.query(
            func.date_trunc('day', Action.timestamp).label('day'),
            Action.status,
            func.count(Action.id)).filter_by(user_id=user_id).group_by(
            'day', Action.status)
        return dict_from_tuples(user_history_stats_query.all())


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
                db.session.add(challenge)
                db.session.commit()

            # Is this the right error?
            return osmerror("ChallengeComplete",
                            "Challenge {} is complete".format(challenge.title))
        if assign:
            task.append_action(Action("assigned", osmid))
            db.session.add(task)

        db.session.commit()
        return marshal(task, task_fields)


class ApiChallengeTaskDetails(ProtectedResource):

    """Task details endpoint"""

    def get(self, slug, identifier):
        """Returns non-geo details for the task identified by
        'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return marshal(task, task_fields)

    def post(self, slug, identifier):
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
        db.session.add(task)
        db.session.commit()
        return {}


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


# Add all resources to the RESTful API
api.add_resource(ApiPing,
                 '/api/ping')
api.add_resource(ApiSelfInfo,
                 '/api/me')
# statistics endpoint
api.add_resource(ApiStats,
                 '/api/stats',
                 '/api/stats/users',
                 '/api/stats/challenge/<string:challenge_slug>',
                 '/api/stats/challenge/<string:challenge_slug>/users',
                 '/api/stats/user/<int:user_id>',
                 '/api/stats/user/<int:user_id>/challenges')
api.add_resource(ApiStatsHistory,
                 '/api/stats/history')
api.add_resource(ApiStatsChallengeHistory,
                 '/api/stats/challenge/<string:challenge_slug>/history')
api.add_resource(ApiStatsUserHistory,
                 '/api/stats/user/<int:user_id>/history')
api.add_resource(ApiChallengeSummaryStats,
                 '/api/stats/challenge/<string:challenge_slug>/summary')
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
api.add_resource(ApiGetAChallenge,
                 '/api/challenge')
api.add_resource(ApiChallengeDetail,
                 '/api/challenge/<string:slug>')
api.add_resource(ApiChallengePolygon,
                 '/api/challenge/<string:slug>/polygon')

#
# The Admin API ################
#


class AdminApiChallenge(Resource):

    """Admin challenge creation endpoint"""

    def put(self, slug):
        if challenge_exists(slug):
            return {}
        try:
            payload = json.loads(request.data)
        except Exception:
            abort(400)
        if not 'title' in payload:
            abort(400)
        c = Challenge(
            slug,
            payload.get('title'),
            payload.get('geometry'),
            payload.get('description'),
            payload.get('blurb'),
            payload.get('help'),
            payload.get('instruction'),
            payload.get('active'),
            payload.get('difficulty'))
        db.session.add(c)
        db.session.commit()
        return {}

    def delete(self, slug):
        """delete a challenge"""
        challenge = get_challenge_or_404(slug)
        db.session.delete(challenge)
        db.session.commit()
        return {}, 204


class AdminApiTaskStatuses(Resource):

    """Admin Task status endpoint"""

    def get(self, slug):
        """Return task statuses for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True, False)
        return [{
            'identifier': task.identifier,
            'status': task.status} for task in challenge.tasks]


class AdminApiUpdateTask(Resource):

    """Challenge Task Statuses endpoint"""

    def put(self, slug, identifier):
        """Create or update one task."""

        # Parse the posted data
        parse_task_json(json.loads(request.data), slug, identifier)
        return {}, 201

    def delete(self, slug, identifier):
        """Delete a task"""

        task = get_task_or_404(slug, identifier)
        task.append_action(Action('deleted'))
        db.session.add(task)
        db.session.commit()
        return {}, 204


class AdminApiUpdateTasks(Resource):

    """Bulk task creation / update endpoint"""

    def put(self, slug):

        app.logger.debug('putting multiple tasks')
        app.logger.debug(len(request.data))
        # Get the posted data
        taskdata = json.loads(request.data)

        for task in taskdata:
            parse_task_json(task, slug, task['identifier'], commit=False)

        # commit all dirty tasks at once.
        db.session.commit()
        return {}, 200

api.add_resource(AdminApiChallenge, '/api/admin/challenge/<string:slug>')
api.add_resource(AdminApiTaskStatuses,
                 '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTasks,
                 '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTask,
                 '/api/admin/challenge/<string:slug>/task/<string:identifier>')
