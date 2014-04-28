#!/usr/bin/env python

import hashlib
import psycopg2
import getpass
from psycopg2.extras import register_hstore, DictCursor
from shapely import wkb
import requests
import grequests
import geojson
import json
import argparse
import logging
from classmaprouletteloader import mapRouletteChallenge,mapRouletteTask
from time import gmtime,strftime

def get_tasks_from_db(args,inputMapRouletteChallenge):
    db_user = args.user
    if not args.user:
        db_user = getpass.getuser()

    db_name = args.database
    if not args.database:
        db_name = 'osm'

    db_query = args.query

    db_string = "dbname={db_name} user={db_user}".format(db_name=db_name,
                                                         db_user=db_user
                                                         )

    if args.host:
        db_string += " host={db_host}".format(db_host=args.host)

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

        mr_challenge.addTask(mapRouletteTask(geom,osmid,mr_challenge.slug,mr_challenge.instruction)) 

    return mr_challenge

def get_tasks_from_json(args,inputMapRouletteChallenge):
    mr_challenge = inputMapRouletteChallenge

    with open(args.json_file, 'r') as infile:
        tasks = json.load(infile)

    for task in tasks:
        osmid = task['geometries']['features'][0]['properties']['osmid']
        geom = task['geometries']
        mr_challenge.addTask(mapRouletteTask(geom,osmid,mr_challenge.slug,mr_challenge.instruction)) 

    return mr_challenge

if __name__ == "__main__":

    logging.basicConfig()
    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.WARNING)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.WARNING)
    requests_log.propagate = True

    # arguments schmarguments
    help_text = 'This script creates a challenge and populates it with tasks \
        from an osmosis schema OSM database or a JSON file with features. \
        \n\
        Run this with the following command:\n\
        python process.py --server <your_server> test1 use-json example.json'

    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument('challenge_slug',
                        help='the MapRoulette challenge slug to add tasks to.')
    parser.add_argument('--title', dest='challenge_title',
                        help='MapRoulette challenge title.\
                        Useful only if the task is created.\
                        Defaults to the challenge slug if not supplied.')
    parser.add_argument('--instruction', dest='challenge_instruction',
                        help='MapRoulette challenge-wide instructions.')
    parser.add_argument('--server',
                        default='http://localhost:5000/',
                        help='the MapRoulette server instance to talk to, \
                        for example http://maproulette.org/. \
                        Defaults to http://localhost:5000/. \
                        Must have a trailing slash!')
    parser.add_argument('--dry',
                        default=False,
                        action='store_true',
                        help='dry run: no connection will be made, and no \
                        content will be sent.')
    parser.add_argument('--force-post',
                        default=False,
                        action='store_true',
                        help='execute responses even with dry run set.')
    parser.add_argument('--output',
                        default='responses.json',
                        help='the output file where answer from the server, \
                        are written. \
                        Defaults to responses.json.')
    parser.add_argument('-v', '--verbose',
                        default=False,
                        action='store_true',
                        help='Enable verbose output of http requests')
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='Enable debugging output of http requests')

    subparsers = parser.add_subparsers(help='Specify the source of the tasks')

    # create the parser for the "db" command
    parser_db = subparsers.add_parser('use-db',
                                      help='use a database as the source')
    parser_db.add_argument('query',
                           help='the database query to use')
    parser_db.add_argument('--database',
                           help='name of the database. \
                           Defaults to osm')
    parser_db.add_argument('--user',
                           help='database user. Defaults to the current user')
    parser_db.add_argument('--host',
                           help='database host. Defaults to localhost')

    # create the parser for the "json" command
    parser_json = subparsers.add_parser('use-json', help='JSON help')
    parser_json.add_argument('json_file',
                             help='JSON file with tasks')

    args = parser.parse_args()

    if args.verbose:
        rootlogger.setLevel(logging.INFO)
        requests_log.setLevel(logging.INFO)

    if args.debug:
        rootlogger.setLevel(logging.DEBUG)
        requests_log.setLevel(logging.DEBUG)

    #set slug and challenge title parameters
    slug = args.challenge_slug

    challenge_title = args.challenge_title
    if not args.challenge_title:
        challenge_title = slug

    #instatiate maproulette challenge loading object
    mrChallengeLoader = mapRouletteChallenge(args.server,slug,challenge_title)

    #maproulette challenge loading object checks for server existence
    if not args.dry and not mrChallengeLoader.serverExists:
        print 'There is no running MapRoulette API instance at {}'.format(base)
        print 'You can supply a MR server URL with the --server option.'
        exit(0)

    #maproulette challenge loading object checks if challenge exists, if not it creates a new one
    mrChallengeLoader.initChallenge()

    #adds tasks to task payload, by data source
    if 'query' in args:
        mrChallengeLoader = get_tasks_from_db(args,mrChallengeLoader)

    if 'json_file' in args:
        mrChallengeLoader = get_tasks_from_json(args,mrChallengeLoader)

    bulkTaskUploadResponse = mrChallengeLoader.uploadTasks
    with open(args.output, 'a+') as outfile:
        outfile.write(strftime('%Y-%m-%d %H:%M:%S', gmtime())+','+str(bulkTaskUploadResponse.json()['status'])+','+str(bulkTaskUploadResponse.json()['message']))

    outfile.close()

    print '\ndone.'
