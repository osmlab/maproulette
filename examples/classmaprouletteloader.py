import hashlib
import psycopg2
from psycopg2.extras import register_hstore, DictCursor
import json
import requests


##MAPROULETTE CHALLENGE AND TASK LOADER CLASSES AND METHODS
class mapRouletteChallenge(object):
    def __init__(self,server,challengeSlug,challengeTitle=None,challengeInstruction=None):
        self.base = server + 'api'
        self.getchallenge_endpoint = self.base + 'challenge/{slug}'
        self.api_createchallenge_endpoint = self.base + 'admin/challenge/{slug}'
        self.api_addtask_endpoint = self.base + 'admin/challenge/{slug}/task/{id}'
        self.slug = challengeSlug
        self.title = challengeTitle
        self.instruction = challengeInstruction        
        self.payload = []
        self.challengeExists = False

        #checks if server is running instance of maproulette
        try:
            r = requests.get(base + 'ping')
            if r.status_code == 200:
                print 'MapRoulette API Service Exists!'
        except requests.exceptions.ConnectionError:
            print 'MapRoulette API Service Doesn\'t seem to exist!\nEnding challenge creation.'
            return False

        #Determines if Challenge Exists or not
        response = requests.get(self.getchallenge_endpoint.format(slug=self.slug))
        if response.status_code == 200:
            self.challengeExists = True
            self.title = response.json()['title']
            self.instruction = response.json()['instruction']
            print 'Challenge slug {slug}'.format(slug=self.slug),'exists.\n'
        elif response.status_code == 500
            print 'Could not assertain if challenge slug {slug} exists. Internal Server Error (500).\n'.format(slug=self.slug)
        else:
            print 'Challenge slug {slug}'.format(slug=self.slug),' does not exist. Creating challenge.\n'
            createChallengeRequest = requests.put(self.api_createchallenge_endpoint.format(slug=slug),data=json.dumps({"title": self.title, "active": True}))
            if createChallengeRequest.status_code == 200:
                print "Challenge slug {slug} successfully created.\n".format(slug=self.slug)
            else:
                print "Could not create challenge slug {slug}.\n".format(slug=self.slug)
                return False


    def createPayloadFromJSON(self,fileJSON):
        with open(fileJSON, 'r') as infile:
            tasks = json.load(infile)

        for task in tasks:
            osmid = task['geometries']['features'][0]['properties']['osmid']
            geom = task['geometries']

            mrtask = classmaprouletteloader.mapRouletteTask(geom,osmid,self.slug,self.instruction)
            self.payload.append(mrtask.createPayload())


    def createPayloadFromDatabase(self,dbUser,dbQuery,dbHost,dbName=None):
        db_user = dbUser

        db_name = dbName
        if not dbName:
            db_name = 'osm'

        db_query = dbQuery

        db_string = "dbname={db_name} user={db_user}".format(db_name=db_name,
                                                             db_user=db_user
                                                             )

        if dbHost:
            db_string += " host={db_host}".format(db_host=dbHost)

        # open a connection, get a cursor
        conn = psycopg2.connect(db_string)
        cur = conn.cursor(cursor_factory=DictCursor)
        register_hstore(cur)
        # get our results
        cur.execute(db_query)
        nodes = cur.fetchall()

        for node in nodes:
            osmid = node["id"]

            geom = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"osmid": osmid},
                    "geometry": json.loads(geojson.dumps(
                        wkb.loads(node["geom"].decode("hex"))))
                }]
            }        

            mrtask = classmaprouletteloader.mapRouletteTask(geom,osmid,self.slug,self.instruction)
            self.payload.append(mrtask.createPayload())            


class mapRouletteTask(object):
    def __init__(self,geom,osmid,challengeSlug,challengeInstruction=None):
        self.identifier = None
        self.geometries = geom
        self.slug = challengeSlug
        self.osmid = osmid
        self.payload = None

        if instruction == None:
            self.instruction = ''
        else:
            self.instruction = challengeInstruction

    def createPayload(self):
        #creates initial payload dict
        self.payload = {'instruction':self.instruction,'geom':self.geom}

        #generates unique identifier and updates payload (dict)
        digest = hashlib.md5(json.dumps(self.payload)).hexdigest()
        self.identifier = "{slug}-{osmid}-{digest}".format(slug=self.slug,osmid=self.osmid,digest=digest)
        self.payload.update({'identifier':self.identifier})
        
        #returns payload as dict 
        return payload

