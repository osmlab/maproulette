from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource
from flask.ext.restful.fields import Raw
from flask import session, make_response, request, abort
from maproulette.helpers import get_random_task,\
    get_challenge_or_404, get_task_or_404,\
    require_signedin, osmerror, challenge_exists,\
    task_exists
from maproulette.models import User, Challenge, Task, TaskGeometry, Action, db
from sqlalchemy.sql import func
from geoalchemy2.functions import ST_Buffer
from shapely.geometry.base import BaseGeometry
from shapely.geometry import asShape
import geojson
import json
import markdown


class ProtectedResource(Resource):
    """A Resource that requires the caller to be authenticated against OSM"""
    method_decorators = [require_signedin]


class PointField(Raw):
    """An encoded point"""

    def format(self, geometry):
        # if we get a linestring, take the first point,
        # else, just get the point.
        point = geometry.coords[0]
        return '%f|%f' % point


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
    'location': PointField
}

me_fields = {
    'username': fields.String(attribute='display_name'),
    'osm_id': fields.String()
}

action_fields = {
    'task': fields.String(attribute='task_id'),
    'timestamp': fields.DateTime,
    'status': fields.String,
    'user': fields.String(attribute='user_id')
}


api = Api(app)

# override the default JSON representation to support the geo objects


@api.representation('application/json')
def output_json(data, code, headers=None):
    """Automatic JSON / GeoJSON output"""
    # return empty result if data contains nothing
    if not data:
        resp = make_response(geojson.dumps({}), code)
    # if this is a Shapely object, dump it as geojson
    elif isinstance(data, BaseGeometry):
        resp = make_response(geojson.dumps(data), code)
    # if this is a list of task geometries, we need to unpack it
    elif not isinstance(data, dict) and isinstance(data[0], TaskGeometry):
        # unpack the geometries FIXME can this be done in the model?
        geometries = [geojson.Feature(
            geometry=g.geometry,
            properties={
                'selected': True,
                'osmid': g.osmid}) for g in data]
        resp = make_response(
            geojson.dumps(geojson.FeatureCollection(geometries)),
            code)
    # otherwise perform default json representation
    else:
        resp = make_response(json.dumps(data), code)
    # finish and return the response object
    resp.headers.extend(headers or {})
    return resp


class ApiPing(Resource):
    """a simple ping endpoint"""
    def get(self):
        return "I am alive"


class ApiMe(ProtectedResource):
    def get(self):
        me = {}
        challenges = {}
        # select min(a.timestamp) firsttime, count(1), a.status, c.slug from
        # actions a, tasks t, challenges c where a.task_id = t.id and
        # t.challenge_slug = c.slug and a.user_id = 437
        # group by a.status, c.slug;
        for firstaction, lastaction, status,\
            status_count, challenge_slug, challenge_title\
            in db.session.query(
                func.min(Action.timestamp),
                func.max(Action.timestamp),
                Action.status,
                func.count(Action.id),
                Challenge.slug,
                Challenge.title).select_from(Action).filter(
                Action.user_id == session.get('osm_id')).join(
                Task, Challenge).group_by(
                Action.status,
                Challenge.slug,
                Challenge.title).order_by(
                Challenge.title,
                Action.status):
            if challenge_slug in challenges.keys():
                challenges[challenge_slug]['statuses'].update({
                    status: {'first': str(firstaction),
                             'last': str(lastaction),
                             'count': status_count}
                })
            else:
                challenges[challenge_slug] = {
                    'title': challenge_title,
                    'statuses': {
                        status: {'first': str(firstaction),
                                 'last': str(lastaction),
                                 'count': status_count}}
                }
        me['challenges'] = challenges
        return me


class ApiGetAChallenge(ProtectedResource):
    @marshal_with(challenge_summary)
    def get(self):
        """Return a single challenge"""
        return get_challenge_or_404(app.config["DEFAULT_CHALLENGE"])


class ApiChallengeList(ProtectedResource):
    """Challenge list endpoint"""

    @marshal_with(challenge_summary)
    def get(self):
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
                            help='difficulty cannot be parsed')
        parser.add_argument('lon', type=float,
                            help="lon cannot be parsed")
        parser.add_argument('lat', type=float,
                            help="lat cannot be parsed")
        args = parser.parse_args()

        difficulty = None
        contains = None

        # Try to get difficulty from argument, or users preference
        difficulty = args['difficulty']

        # for local challenges, first look at lon / lat passed in
        if args.lon is not None and args.lat is not None:
            contains = 'POINT(%s %s)' % (args.lon, args.lat)
        # if there is none, look at the user's home location from OSM
        #elif 'home_location' in session:
        #    contains = 'POINT(%s %s)' % tuple(session.get('home_location'))

        # get the list of challenges meeting the criteria
        query = db.session.query(Challenge).filter_by(active=True)

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


class ApiChallengePolygon(ProtectedResource):
    """Challenge geometry endpoint"""

    def get(self, slug):
        """Return the geometry (spatial extent)
        for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return challenge.polygon


class ApiStatsChallenge(ProtectedResource):
    """Challenge Statistics endpoint"""

    def get(self, slug):
        """Return statistics for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        total = len(challenge.tasks)
        available = challenge.tasks_available
        return {'total': total, 'available': available}


class ApiStatsChallengeUsers(ProtectedResource):
    """Challenge User Statistics endpoint"""
    def get(self, slug):
        # what we want is
        # * number of unique users participating
        # * number of things fixed per user
        statuses = {}

        # select count(1), u.display_name, a.status from
        # challenges c, users u, tasks t, actions a where
        # c.slug = t.challenge_slug and a.user_id = u.id and
        # a.task_id = t.id and c.slug = 'test10' group by a.status,
        # u.display_name;
        for cnt, display_name, status in db.session.query(
            func.count(User.id),
            User.display_name,
            Action.status).select_from(Action).filter(
            Challenge.slug == slug).join(
            Task, Challenge).group_by(
            Action.status,
            User.display_name).order_by(
                User.display_name,
                Action.status):
            if status in statuses:
                statuses[status].update({
                    display_name: cnt
                })
            else:
                statuses[status] = {
                    display_name: cnt
                }
        return statuses


class ApiStatsUser(ProtectedResource):
    """summary statistics for all users"""
    def get(self):
        pass


class ApiStatsChallenges(ProtectedResource):
    """summary statistics for all challenges"""
    def get(self):
        challenges = {}
        # select count(t.id), t.currentaction, c.slug, c.title from
        # actions a, tasks t, challenges c where a.task_id = t.id and
        #t.challenge_slug = c.slug group by t.currentaction, c.slug, c.title;
        q = db.session.query(
            func.count(Task.id),
            Challenge.slug,
            Challenge.title,
            Task.currentaction).select_from(Task).join(
            Challenge).group_by(
            Task.currentaction,
            Challenge.slug,
            Challenge.title).order_by(
            Challenge.title,
            Task.currentaction)
        for status_count,\
            challenge_slug,\
            challenge_title,\
                status in q:
                if challenge_slug in challenges.keys():
                    challenges[challenge_slug]['statuses'].update({
                        status: status_count})
                else:
                    challenges[challenge_slug] = {
                        'title': challenge_title,
                        'statuses': {status: status_count}
                    }
        return challenges


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

        app.logger.info(
            "{user} requesting task from {challenge} near\
             ({lon}, {lat}) assiging: {assign}".format(
            user=osmid,
            challenge=slug,
            lon=lon,
            lat=lat,
            assign=assign))

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
            # Is this the right error?
            return osmerror("ChallengeComplete",
                            "Challenge {} is complete".format(slug))
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
        app.logger.debug('updating task %s' % (identifier, ))
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
        return {'status': task.currentaction}


class ApiChallengeTaskGeometries(ProtectedResource):
    """Task geometry endpoint"""

    def get(self, slug, identifier):
        """Returns the geometries for the task identified by
        'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return task.geometries

# Add all resources to the RESTful API
api.add_resource(ApiPing,
                 '/api/ping')
api.add_resource(ApiSelfInfo,
                 '/api/me')
# statistics endpoints
# basic stats for one challenge
api.add_resource(ApiStatsChallenge,
                 '/api/stats/challenge/<string:slug>')
# detailed user breakdown for one challenge
api.add_resource(ApiStatsChallengeUsers,
                 '/api/stats/challenge/<string:slug>/users')
# summary stats for all challenges
api.add_resource(ApiStatsChallenges,
                 '/api/stats/challenges')
# summary stats for all users
api.add_resource(ApiStatsUser,
                 '/api/stats/users')
# stats about the signed in user
api.add_resource(ApiMe,
                 '/api/stats/me')
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

################################
# The Admin API ################
################################


class AdminApiChallenge(Resource):
    """Admin challenge creation endpoint"""
    def put(self, slug):
        if challenge_exists(slug):
            app.logger.debug('challenge exists')
            abort(400)
        try:
            payload = json.loads(request.data)
        except Exception:
            app.logger.debug('payload invalid, no json')
            abort(400)
        if not 'title' in payload:
            app.logger.debug('payload invalid, no title')
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

    def delete(self, slug):
        """delete a challenge"""
        challenge = get_challenge_or_404(slug)
        db.session.delete(challenge)
        db.session.commit()


class AdminApiTaskStatuses(Resource):
    """Admin Task status endpoint"""

    def get(self, slug):
        """Return task statuses for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return [{
            'identifier': task.identifier,
            'status': task.currentaction} for task in challenge.tasks]


class AdminApiUpdateTask(Resource):
    """Challenge Task Statuses endpoint"""

    def put(self, slug, identifier):
        """Create or update one task. By default, the
        geometry must be supplied as WKB, but this can
        be overridden by adding ?geoformat=geojson to
        the URL"""

        task_geometries = []

        # Get the posted data
        taskdata = json.loads(request.data)

        exists = task_exists(slug, identifier)

        app.logger.debug("taskdata: %s" % (taskdata,))

        # abort if the taskdata does not contain geometries and it's a new task
        if not 'geometries' in taskdata:
            if not exists:
                abort(400)
        else:
            # extract the geometries
            geometries = taskdata.pop('geometries')
            app.logger.debug("geometries: %s" % (geometries,))
            app.logger.debug("features: %s" % (geometries['features'],))

            # parse the geometries
            for feature in geometries['features']:
                app.logger.debug(feature)
                osmid = feature['properties'].get('osmid')
                shape = asShape(feature['geometry'])
                t = TaskGeometry(osmid, shape)
                task_geometries.append(t)

        # there's two possible scenarios:
        # 1.    An existing task gets an update, in that case
        #       we only need the identifier
        # 2.    A new task is inserted, in this case we need at
        #       least an identifier and encoded geometries.

        # now we check if the task exists
        if exists:
            # if it does, update it
            app.logger.debug('existing task')
            task = get_task_or_404(slug, identifier)
            if not task.update(taskdata, task_geometries):
                abort(400)
        else:
            # if it does not, create it
            app.logger.debug('new task')
            new_task = Task(slug, identifier)
            new_task.update(taskdata, task_geometries)
        return {}

    def delete(self, slug, identifier):
        """Delete a task"""

        task = get_task_or_404(slug, identifier)
        task.append_action(Action('deleted'))
        db.session.add(task)
        db.session.commit()

api.add_resource(AdminApiChallenge, '/api/admin/challenge/<string:slug>')
api.add_resource(AdminApiTaskStatuses,
                 '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTask,
                 '/api/admin/challenge/<string:slug>/task/<string:identifier>')
