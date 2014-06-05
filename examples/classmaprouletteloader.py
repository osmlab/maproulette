import hashlib
import json
import requests

##MAPROULETTE CHALLENGE AND TASK LOADER CLASSES AND METHODS
class mapRouletteChallenge(object):
    def __init__(self,server,challengeSlug,challengeTitle=None,challengeInstruction=None):
        self.base = server + 'api/'
        self.getchallenge_endpoint = self.base + 'challenge/{slug}'
        self.api_createchallenge_endpoint = self.base + 'admin/challenge/{slug}'
        self.api_addtask_endpoint = self.base + 'admin/challenge/{slug}/task/{id}'
        self.api_addbulktask_endpoint = self.base + 'admin/challenge/{slug}/tasks'
        self.slug = challengeSlug
        self.title = challengeTitle
        self.instruction = challengeInstruction        
        self.payload = []
        self.challengeExists = False
        self.serverExists = False

        #checks if server is running instance of maproulette api
        try:
            r = requests.get(self.base + 'ping')
            if r.status_code == 200:
                print 'MapRoulette API Service Exists!\n'
                self.serverExists = True
                return None
            else:
                print 'MapRoulette API Service Doesn\'t seem to exist!\n'                           
        except requests.exceptions.ConnectionError:
            print 'MapRoulette API Service Doesn\'t seem to exist!\n'

        print 'Ending challenge creation.\n'                   

    def initChallenge(self):
        #Determines if an active challenge Exists or not
        response = requests.get(self.getchallenge_endpoint.format(slug=self.slug))
        if (response.status_code == 200) and (response.json()['active']==True): #and the challenge is active
            self.challengeExists = True
            self.title = response.json()['title']
            self.instruction = response.json()['instruction']
            print 'An active challenge slug, {slug},'.format(slug=self.slug),'exists.\n'
        elif response.status_code == 500:
            print 'Could not assertain if challenge slug {slug} exists. Internal Server Error (500).\n'.format(slug=self.slug)
        else:
            print 'Challenge slug {slug}'.format(slug=self.slug),' does not exist. Creating challenge.\n'
            createChallengeRequest = requests.put(self.api_createchallenge_endpoint.format(slug=self.slug),data=json.dumps({"title": self.title, "active": True}))
            if createChallengeRequest.status_code == 200:
                print 'Challenge slug {slug} successfully created.\n'.format(slug=self.slug)
                self.challengeExists = True
            else:
                print 'Could not create challenge slug {slug}.\n'.format(slug=self.slug)
                return [False,'Could not create challenge slug {slug}.\n'.format(slug=self.slug)]

    def addTask(self,inputMRTask):
        #adds task dict to dict array of tasks (bulk payload). 
        self.payload.append(inputMRTask.createPayload())

    def uploadTasks(self):
        #converts dict payload to JSON. Then uploads tasks to MapRoulette Server.
        headers = {'content-type': 'application/json'}
        requestData = json.dumps(self.payload)
        taskUploadRequest = requests.put(self.api_addbulktask_endpoint.format(slug=self.slug),data=requestData,headers=headers)  
        return taskUploadRequest

class mapRouletteTask(object):
    def __init__(self,geom,osmid,challengeSlug,challengeInstruction=None):
        self.identifier = None
        self.geom = geom
        self.slug = challengeSlug
        self.osmid = osmid
        self.payload = None

        if challengeInstruction == None:
            self.instruction = ''
        else:
            self.instruction = challengeInstruction

    def createPayload(self):
        #creates initial payload dict
        self.payload = {'instruction':self.instruction,'geometries':self.geom}

        #generates unique identifier and updates task payload (dict)
        digest = hashlib.md5(json.dumps(self.payload)).hexdigest()
        self.identifier = "{slug}-{osmid}-{digest}".format(slug=self.slug,osmid=self.osmid,digest=digest)
        self.payload.update({'identifier':self.identifier})
        
        #returns payload as dict 
        return self.payload
