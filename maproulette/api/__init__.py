from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, \
    marshal_with, Api, Resource
from flask.ext.restful.fields import get_value, Raw
from flask.ext.sqlalchemy import get_debug_queries
from flask import session, make_response
from maproulette.helpers import GeoPoint, get_challenge_or_404, \
    get_task_or_404, get_random_task, osmlogin_required, osmerror
from maproulette.models import Challenge, Task, TaskGeometry, Action, db
from geoalchemy2.functions import ST_Buffer
from shapely import geometry
import geojson
import json


class ProtectedResource(Resource):

    method_decorators = [osmlogin_required]


class PointField(Raw):

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
    # return empty result if data contains nothing
    if not data:
        resp = make_response(geojson.dumps({}), code)
    # if this is a Shapely object, sump it as geojson
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

    def get(self, slug):
        challenge = get_challenge_or_404(slug, True)
        return marshal(challenge, challenge.marshal_fields)


class ApiChallengePolygon(ProtectedResource):

    def get(self, slug):
        challenge = get_challenge_or_404(slug, True)
        return challenge.polygon


class ApiChallengeStats(ProtectedResource):

    def get(self, slug):
        challenge = get_challenge_or_404(slug, True)
        total = Task.query.filter(slug == challenge.slug).count()
        tasks = Task.query.filter(slug == challenge.slug).all()
        osmid = session.get('osm_id')
        available = len([task for task in tasks
                         if challenge.task_available(task, osmid)])
        app.logger.info(
            "{user} requested challenge stats for {challenge}".format(
                user=osmid, challenge=slug))
        return {'total': total, 'available': available}


class ApiChallengeTask(ProtectedResource):

    def get(self, slug):
        "Returns a task for specified challenge"
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

    def get(self, slug, identifier):
        task = get_task_or_404(slug, identifier)
        return marshal(task, task_fields)

    def post(self, slug, identifier):
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
        task.actions.append(Action(args.action,
                                   session.get('osm_id'),
                                   args.editor))
        db.session.add(task)
        db.session.commit()
        return {'message': 'OK'}


class ApiChallengeTaskGeometries(ProtectedResource):

    def get(self, slug, identifier):
        task = get_task_or_404(slug, identifier)
        return task.geometries

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
