from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource
from flask.ext.restful.fields import get_value, Raw
from flask.ext.sqlalchemy import get_debug_queries
from flask import session, make_response, request
from maproulette.helpers import *
from maproulette.models import Challenge, Task, TaskGeometry, Action, db
from geoalchemy2.functions import ST_Buffer
from shapely.geometry.base import BaseGeometry
from shapely.geometry import asShape
from shapely import wkb
import geojson
import json


class ProtectedResource(Resource):
    """A Resource that requires the caller to be authenticated against OSM"""
    method_decorators = [osmlogin_required]


class PointField(Raw):
    """An encoded point"""

    def format(self, geometry):
        # if we get a linestring, take the first point,
        # else, just get the point.
        point = geometry.coords[0]
        return '%f|%f' % point

challenge_summary = {
    'slug': fields.String,
    'title': fields.String,
    'difficulty': fields.Integer,
    'description': fields.String,
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
    app.logger.debug(data)
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

class ApiChallengeList(ProtectedResource):
    """Challenge list endpoint"""

    @marshal_with(challenge_summary)
    def get(self):
        """returns a list of challenges.
        Optional URL parameters are:
        difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
        lon/lat: the coordinate to filter on (returns only
        challenges whose bounding polygons contain this point)
        example: /api/challenges?lon=-100.22&lat=40.45&difficulty=2
        all: if true, return all challenges regardless of OSM user home location
        """
        # initialize the parser
        parser = reqparse.RequestParser()
        parser.add_argument('difficulty', type=int, choices=["1", "2", "3"],
                            help='difficulty cannot be parsed')
        parser.add_argument('lon', type=float,
                            help="lon cannot be parsed")
        parser.add_argument('lat', type=float,
                            help="lat cannot be parsed")
        parser.add_argument('all', type=bool,
                            help="all cannot be parsed")
        args = parser.parse_args()

        difficulty = None
        contains = None

        # Try to get difficulty from argument, or users preference
        difficulty = args['difficulty'] or session.get('difficulty')

        # for local challenges, first look at lon / lat passed in
        if args.lon and args.lat:
            contains = 'POINT(%s %s)' % (args.lon, args.lat)
        # if there is none, look at the user's home location from OSM
        elif 'home_location' in session:
            contains = 'POINT(%s %s)' % tuple(session['home_location'])

        # get the list of challenges meeting the criteria
        query = db.session.query(Challenge).filter(Challenge.active == True)

        if difficulty:
            query = query.filter(Challenge.difficulty == difficulty)
        if contains and not args.all:
            query = query.filter(Challenge.polygon.ST_Contains(contains))

        challenges = query.all()
        app.logger.debug(get_debug_queries())

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
        if session.osm_auth:
            return marshal(session, me_fields)
        else:
            return json.dumps({'username': None, 'osm_id': None})

class ApiChallengePolygon(ProtectedResource):
    """Challenge geometry endpoint"""

    def get(self, slug):
        """Return the geometry (spatial extent) for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return challenge.polygon


class ApiChallengeStats(ProtectedResource):
    """Challenge Statistics endpoint"""

    def get(self, slug):
        """Return statistics for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        total = len(challenge.tasks)
        # for task in Task.query.filter(Task.challenge_slug == slug):
        #    app.logger.debug(task.available)
        available = challenge.tasks_available
        return {'total': total, 'available': available}


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
            "{user} requesting task from {challenge} near ({lon}, {lat}) assiging: {assign}".format(
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
        if task is None:  # we did not get a lon/lat or there was no task close to there
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
        """Returns non-geo details for the task identified by 'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return marshal(task, task_fields)

    def post(self, slug, identifier):
        """Update the task identified by 'identifier' from the challenge identified by 'slug'"""
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
        return {'message': 'OK'}


class ApiChallengeTaskStatus(ProtectedResource):
    """Task status endpoint"""

    def get(self, slug, identifier):
        """Returns current status for the task identified by 'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        app.logger.debug(task.currentaction)
        return {'status': task.currentaction}

class ApiChallengeTaskGeometries(ProtectedResource):
    """Task geometry endpoint"""

    def get(self, slug, identifier):
        """Returns the geometries for the task identified by 'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return task.geometries

# Add all resources to the RESTful API
api.add_resource(ApiPing, '/api/ping')
api.add_resource(ApiChallengeList, '/api/challenges/')
api.add_resource(ApiChallengeDetail, '/api/challenge/<string:slug>/')
api.add_resource(ApiChallengePolygon, '/api/challenge/<string:slug>/polygon/')
api.add_resource(ApiChallengeStats, '/api/challenge/<string:slug>/stats/')
api.add_resource(ApiChallengeTask, '/api/challenge/<slug>/task/')
api.add_resource(ApiSelfInfo, '/api/me')
api.add_resource(
    ApiChallengeTaskDetails,
    '/api/challenge/<slug>/task/<identifier>/')
api.add_resource(
    ApiChallengeTaskGeometries,
    '/api/challenge/<slug>/task/<identifier>/geometries/')
api.add_resource(
    ApiChallengeTaskStatus,
    '/api/challenge/<slug>/task/<identifier>/status/')

################################
# The Admin API ################
################################

class AdminApiChallengeCreate(ProtectedResource):
    """Admin challenge creation endpoint"""
    def put(self, slug):
        if challenge_exists(slug):
            app.logger.debug('challenge exists')
            abort(403)
        try:
            payload = json.loads(request.data)
        except Exception, e:
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

class AdminApiTaskStatuses(ProtectedResource):
    """Admin Task status endpoint"""

    def get(self, slug):
        """Return task statuses for the challenge identified by 'slug'"""
        challenge = get_challenge_or_404(slug, True)
        return [{
            'identifier': task.identifier,
            'status': task.currentaction} for task in challenge.tasks]

class AdminApiUpdateTask(ProtectedResource):
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
        return {"message": "ok"}

    def delete(self, slug, identifier):
        """Delete a task"""

        task = get_task_or_404(slug,identifier)
        task.append_action(Action('deleted'))
        db.session.add(task)
        db.session.commit()

api.add_resource(AdminApiChallengeCreate, '/api/admin/challenge/<string:slug>')
api.add_resource(AdminApiTaskStatuses, '/api/admin/challenge/<string:slug>/tasks')
api.add_resource(AdminApiUpdateTask, '/api/admin/challenge/<string:slug>/task/<string:identifier>')
