from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, Api, Resource
from flask.ext.restful.fields import get_value, Raw
from flask import session
from maproulette.helpers import GeoPoint, get_challenge_or_404
from maproulette.models import Challenge, Task, Action, db

class GeoJsonField(Raw):
    """A GeoJson Representation of an Shapely object"""

    def output(self, key, obj):
        value = get_value(key if self.attribute is None else self.attribute, obj)
        if value is None:
            return self.default
        else:
            value = geojson.loads(value)            
        return self.format(value)
        
challenge_fields = {
    'id':           fields.String(attribute='slug'),
    'title':        fields.String,
    'description':  fields.String,
    'blurb':        fields.String,
    'help':         fields.String,
    'instruction':  fields.String,
    'active':       fields.Boolean,
    'difficulty':   fields.Integer,
    'polygon':      GeoJsonField
}

task_fields = {
    'id':           fields.String(attribute='identifier'),
    'location':     GeoJsonField,
    'manifest':     GeoJsonField,
    'text':         fields.String(attribute='instructions')
}

api = Api(app)

class ApiChallengeList(Resource):
    def get(self):
        """returns a list of challenges.
        Optional URL parameters are:
        difficulty: the desired difficulty to filter on (1=easy, 2=medium, 3=hard)
        contains: the coordinate to filter on (as lon|lat, returns only
        challenges whose bounding polygons contain this point)
        example: /api/c/challenges?contains=-100.22|40.45&difficulty=2
        """

        # initialize the parser
        parser = reqparse.RequestParser()
        parser.add_argument('difficulty', type=int, choices=["1","2","3"],
                            help='difficulty cannot be parsed')
        parser.add_argument('contains', type=GeoPoint,
                            help="Could not parse contains")
        args = parser.parse_args()
        
        # Try to get difficulty from argument, or users prefers or default
        difficulty = args['difficulty'] or session.get('difficulty') or 1
        
        # Try to get location from argument or user prefs
        contains = None
        
        if args['contains']:
            contains = args['contains']
            coordWKT = 'POINT(%s %s)' % (contains.lat, contains.lon)
        elif 'home_location' in session:
            contains = session['home_location']
            coordWKT = 'POINT(%s %s)' % tuple(contains.split("|"))
            app.logger.debug('home location retrieved from session')
        
        # get the list of challenges meeting the criteria
        query = db.session.query(Challenge)
        if difficulty:
            query = query.filter(Challenge.difficulty==difficulty)
        if contains:
            query = query.filter(Challenge.geom.ST_Contains(coordWKT))

        challenges = [marshal(challenge, challenge_fields)
                      for challenge in query.all() if challenge.active]
        
        #if there are no near challenges, return anything
        if len(challenges) == 0:
            app.logger.debug('we have nothing close, looking all over within difficulty setting')
            challenges = [marshal(challenge, challenge_fields)
                          for challenge in db.session.query(Challenge).\
                              filter(Challenge.difficulty==difficulty).all()
                          if challenge.active]
                          
        # what if we still don't get anything? get anything!
        if len(challenges) == 0:
            app.logger.debug('we still have nothing, returning any challenge')
            challenges = [marshal(challenge, challenge_fields)
                          for challenge in db.session.query(Challenge).all()
                          if challenge.active]    

        app.logger.debug(challenges)
        return challenges

class ApiChallengeDetail(Resource):
    def get(self, slug):
        app.logger.debug('retrieving challenge %s' % (slug,))
        return marshal(
            get_challenge_or_404(slug),
            challenge_fields)
        
class ApiChallengeStats(Resource):
    def get(self, slug):
        challenge = get_challenge_or_404(slug, True)
        
        total = Task.query.filter(slug == challenge.slug).count()
        tasks = Task.query.filter(slug == challenge.slug).all()
        osmid = session.get('osm_id')
        available = len([task for task in tasks
                         if challenge.task_available(task, osmid)])
        
        logging.info("{user} requested challenge stats for {challenge}".format(
                user=osmid, challenge=slug))
                
        return {'total': total, 'available': available}

api.add_resource(ApiChallengeList, '/api/challenges/')
api.add_resource(ApiChallengeDetail, '/api/challenge/<string:slug>')
api.add_resource(ApiChallengeStats, '/api/challenge/<string:slug>/stats')
