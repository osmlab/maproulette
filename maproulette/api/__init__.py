from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource
from flask.ext.restful.fields import get_value, Raw
from flask.ext.sqlalchemy import get_debug_queries
from flask import session, make_response
from maproulette.helpers import get_challenge_or_404, \
    get_task_or_404, get_random_task, osmlogin_required, osmerror
from maproulette.models import Challenge, Task, TaskGeometry, Action, db
from geoalchemy2.functions import ST_Buffer
from shapely import geometry
import geojson
import json


class ProtectedResource(Resource):
    """A Resource that requires the caller to be authenticated against OSM"""
    method_decorators = [osmlogin_required]


class PointField(Raw):
    """An encoded point"""

    def format(self, value):
        return '|'.join([str(value.x), str(value.y)])

challenge_summary = {
    'slug': fields.String,
    'title': fields.String,
    'difficulty': fields.Integer,
    'islocal': fields.Boolean
}

task_fields = {
    'id': fields.String(attribute='identifier'),
    'text': fields.String(attribute='instruction'),
    'location': PointField
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
    elif isinstance(data, geometry.base.BaseGeometry):
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


class ApiChallengeList(ProtectedResource):
    """Challenges endpoint"""

    @marshal_with(challenge_summary)
    def get(self):
        """returns a list of challenges.
        Optional URL parameters are:
        difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
        lon/lat: the coordinate to filter on (returns only
        challenges whose bounding polygons contain this point)
        example: /api/c/challenges?lon=-100.22&lat=40.45&difficulty=2
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
        if not task:  # we did not get a lon/lat or there was no task close to there
            # If no location is specified, or no tasks were found, gather
            # random tasks
            task = get_random_task(challenge)
            # If no tasks are found with this method, then this challenge
            # is complete
        if not task:
            # Is this the right error?
            osmerror("ChallengeComplete",
                     "Challenge {} is complete".format(slug))
        if assign:
            task.actions.append(Action("assigned", osmid))
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
        task.actions.append(Action(args.action,
                                   session.get('osm_id'),
                                   args.editor))
        # then set the tasks availability based on this
        if args.action in ['fixed', 'falsepositive', 'alreadyfixed']:
            task.available = False
        else:
            task.available = True
        db.session.add(task)
        db.session.commit()
        return {'message': 'OK'}


class ApiChallengeTaskStatus(ProtectedResource):
    """Task status endpoint"""

    def get(self, slug, identifier):
        """Returns current status for the task identified by 'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return task.currentaction


class ApiChallengeTaskGeometries(ProtectedResource):
    """Task geometry endpoint"""

    def get(self, slug, identifier):
        """Returns the geometries for the task identified by 'identifier' from the challenge identified by 'slug'"""
        task = get_task_or_404(slug, identifier)
        return task.geometries

# Add all resources to the RESTful API
api.add_resource(ApiChallengeList, '/api/challenges/')
api.add_resource(ApiChallengeDetail, '/api/challenge/<string:slug>')
api.add_resource(ApiChallengePolygon, '/api/challenge/<string:slug>/polygon')
api.add_resource(ApiChallengeStats, '/api/challenge/<string:slug>/stats')
api.add_resource(ApiChallengeTask, '/api/challenge/<slug>/task')
api.add_resource(
    ApiChallengeTaskDetails,
    '/api/challenge/<slug>/task/<identifier>')
api.add_resource(
    ApiChallengeTaskGeometries,
    '/api/challenge/<slug>/task/<identifier>/geometries')
api.add_resource(
    ApiChallengeTaskStatus,
    '/api/challenge/<slug>/task/<identifier>/status')
