import psycopg2
from psycopg2.extras import register_hstore, DictCursor
from shapely import wkb
import requests
import geojson
import json 

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

# the MapROulette API endpoint
mr_api_endpoint = "http://localhost:3000/api/admin/challenge/{slug}/task/{id}"

# open a connection, get a cursor
conn = psycopg2.connect("dbname={db_name} user={db_user}".format(db_name=db_name, db_user=db_user))
cur = conn.cursor(cursor_factory=DictCursor)
register_hstore(cur)

# get our results
cur.execute(db_query)
nodes = cur.fetchall()

def create_challenge_if_not_exists(slug):
	"""This function creates the MR challenge if it does not already exist"""
	mr_api_endpoint = "http://localhost:3000/api/challenge/{slug}".format(slug=slug)
	r = requests.get(mr_api_endpoint)
	if not r.status_code == 200:
		print "creating challenge"
		r = requests.put(
			"http://localhost:3000/api/admin/challenge/{slug}".format(slug=slug),
			data=json.dumps({"title": challenge_title, "active": True})
		)
		print r.status_code

create_challenge_if_not_exists(challenge_slug)

# insert all the tasks now.
for node in nodes:
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
		mr_api_endpoint.format(
			slug=challenge_slug, 
			id=identifier), 
		data=payload, 
		headers=headers)
