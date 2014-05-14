import os
import json

from classmaprouletteloader import mapRouletteChallenge, mapRouletteTask

#constructing mapRouletteChallenge object,verifying API service exists
testchallenge=mapRouletteChallenge('http://192.168.1.12:5000/','testchallenge',challengeTitle='this is a test',challengeInstruction='test are instructions')

#creating challenge via API call
testchallenge.initChallenge()

#sample upload json objects/tasks
with open('example2.json', 'r') as infile:
    tasks = json.load(infile)

for task in tasks:
    osmid = task['geometries']['features'][0]['properties']['osmid']
    geom = task['geometries']
    testchallenge.addTask(mapRouletteTask(geom,osmid,testchallenge.slug,testchallenge.instruction)) 

httpresponse = testchallenge.uploadTasks()

