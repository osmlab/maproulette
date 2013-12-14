from maproulette import app
from flask.ext.restful import reqparse, fields, marshal, Api, Resource
from flask.ext.restful.fields import get_value, Raw
from flask import session
from maproulette.helpers import GeoPoint, get_challenge_or_404, \
    get_random_task
from maproulette.models import Challenge, Task, Action, db
import geojson 

class GeoJsonField(Raw):
    """A GeoJson Representation of an Shapely object"""

    def output(self, key, obj):
        value = get_value(key if self.attribute is None else self.attribute, obj)
        if value is None:
            return self.default
        else:
            app.logger.debug(value)
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

class ApiChallengeTaskList(Resource):
    def get(self, slug):
        "Returns a task for specified challenge"
        challenge = get_challenge_or_404(slug, True)
        parser = reqparse.RequestParser()
        parser.add_argument('num', type=int, default=1,
                            help='Number of return results cannot be parsed')
        parser.add_argument('near', type=GeoPoint,
                            help='Near argument could not be parsed')
        parser.add_argument('assign', type=int, default=1,
                            help='Assign could not be parsed')
        args = parser.parse_args()
        osmid = session.get('osm_id')
        # By default, we return a single task, but no more than 10
        num = min(args['num'], 10)
        assign = args['assign']
        near = args['near']
        
        app.logger.info("{user} requesting {num} tasks from {challenge} near {near} assiging: {assign}".format(user=osmid, num=num, challenge=slug, near=near, assign=assign))
        
        task_list = []
        if near:
            coordWKT = 'POINT(%s %s)' % (near.lat, near.lon)
            task_query = Task.query.filter(Task.location.ST_Intersects(
                    ST_Buffer(coordWKT, app.config["NEARBUFFER"]))).limit(num)
            task_list = [task for task in task_query
                         if challenge.task_available(task, osmid)]
        if not near or not task_list:
            # If no location is specified, or no tasks were found, gather
            # random tasks
            task_list = [get_random_task(challenge) for _ in range(num)]
            task_list = filter(None, task_list)
            # If no tasks are found with this method, then this challenge
            # is complete
        if not task_list:
            # Is this the right error?
            osmerror("ChallengeComplete",
                     "Challenge {} is complete".format(slug))
        if assign:
            for task in task_list:
                action = Action(task.id, "assigned", osmid)
                task.current_state = action
                db.session.add(action)
                db.session.add(task)
            db.session.commit()
        
        app.logger.info(
            "{num} tasks found matching criteria".format(num=len(task_list)))
        
        tasks = [marshal(task, task_fields) for task in task_list]

        for query in get_debug_queries():
            app.logger.debug(query)

        return tasks


api.add_resource(ApiChallengeList, '/api/challenges/')
api.add_resource(ApiChallengeDetail, '/api/challenge/<string:slug>')
api.add_resource(ApiChallengeStats, '/api/challenge/<string:slug>/stats')
api.add_resource(ApiChallengeTaskList, '/api/challenge/<slug>/tasks')
