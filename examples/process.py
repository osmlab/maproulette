#!/usr/bin/env python

import psycopg2
from psycopg2.extras import register_hstore, DictCursor
from shapely import wkb
import requests
import geojson
import json 
import argparse
import sys

# This script creates a challenge and populates it with 
# tasks from an osmosis schema OSM database. 

# Database credentials, assuming localhost
db_name  = "osm"
db_user  = "martijnv"

# the query to run, this is for shops with no opening hours
db_query = "SELECT * FROM nodes WHERE tags?'shop' AND NOT tags?'opening_hours';"

# basic challenge info
challenge_slug = "shopswithnohours"
challenge_title = "Shops without Opening Hours"

def is_running_instance(api_url):
	try:
		r = requests.get(base + 'ping')
		return r.status_code == 200
	except requests.exceptions.ConnectionError:
		return False

def create_challenge_if_not_exists(slug):
	"""This function creates the MR challenge if it does not already exist"""
	r = requests.get(mr_api_getchallenge_endpoint.format(slug=slug))
	if not r.status_code == 200:
		print "creating challenge"
		r = requests.put(
			mr_api_createchallenge_endpoint.format(slug=slug),
			data=json.dumps({"title": challenge_title, "active": True})
		)
	print 'challenge existed.'

def post_task(node):
	# get the OSM id
	osmid = node["id"]
	# generate a unique identifier
	identifier = "%s_%i" % (challenge_slug, osmid)
	# construct the geometry geoJSON
	geom = {
		"type" : "FeatureCollection",
		"features": [{
			"type"       : "Feature",
			"properties" : { "osmid": osmid },
			"geometry"   : json.loads(geojson.dumps(wkb.loads(node["geom"].decode("hex"))))
		}]
	}
	# instruction, should be custom for this task, too lazy now
	instruction = "This store has no opening hours attached to it"

	# we have everything, construct the request payload
	payload = json.dumps({
		"instruction": instruction,
		"geometries" : geom})

	# and fire!
	headers = {'content-type': 'application/json'}
	r = requests.put(
		mr_api_addtask_endpoint.format(
			slug=challenge_slug, 
			id=identifier), 
		data=payload, 
		headers=headers)

if __name__ == "__main__":

	# arguments schmarguments
	parser = argparse.ArgumentParser()
	parser.add_argument('--server', 
						default='http://localhost:5000/', 
						help='the MapRoulette server instance to talk to, \
						for example http://maproulette.org/. \
						Defaults to http://localhost:5000/. \
						Must have a trailing slash!')
	parser.add_argument('--query', 
						help='the database query to use (not implemented yet)')
	parser.add_argument('--challenge_slug', 
						help='the MapRoulette challenge slug to add tasks to. \
						(not implemented yet')

	args = parser.parse_args()

	# the MapROulette API endpoints
	base = args.server + "api/"
	# - for getting a challenge
	mr_api_getchallenge_endpoint = base + "challenge/{slug}"
	# - for creating a challenge
	mr_api_createchallenge_endpoint = base + "admin/challenge/{slug}"
	# - for creating a task
	mr_api_addtask_endpoint = base + "admin/challenge/{slug}/task/{id}"

	# check if we got a running MR API instance.
	if not is_running_instance(base):
		print 'There is no running MapRoulette API instance at %s' % (base,)
		print 'You can supply a MR server URL with the --server option.'
		exit(0)

	# if the challenge does not exist, create it.
	create_challenge_if_not_exists(challenge_slug)
	# open a connection, get a cursor
	conn = psycopg2.connect("dbname={db_name} user={db_user}".format(db_name=db_name, db_user=db_user))
	cur = conn.cursor(cursor_factory=DictCursor)
	register_hstore(cur)
	# get our results
	cur.execute(db_query)
	nodes = cur.fetchall()
	print 'posting %i tasks' % (len(nodes),)
	for node in nodes:
		post_task(node)
		sys.stdout.write(".")
		sys.stdout.flush()
	print '\ndone.'