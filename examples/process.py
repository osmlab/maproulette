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


CFS_STATUSES = ('created', 'falsepositive', 'skipped')

HEADERS = {'content-type': 'application/json'}


def is_running_instance(api_url):
    try:
        r = requests.get(base + 'ping')
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def challenge_exists(slug):
    r = requests.get(mr_api_getchallenge_endpoint.format(slug=slug))
    return r.status_code == 200


def create_challenge_if_not_exists(slug, title):
    """This function creates the MR challenge if it does not already exist"""
    if not challenge_exists(slug=slug):
        print "creating challenge"
        r = requests.put(
            mr_api_createchallenge_endpoint.format(slug=slug),
            data=json.dumps({"title": title, "active": True})
        )
    print 'challenge existed.'


def get_tasks_from_db(args):
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

        yield prepare_task(node=node,
                           args=args,
                           osmid=osmid,
                           geom=geom
                           )


def get_tasks_from_json(args):

    with open(args.json_file, 'r') as infile:
        tasks = json.load(infile)
        if isinstance(tasks, dict):
            tasks = [tasks]

    for task in tasks:
        if not args.close:
            import pdb
            pdb.set_trace()
            osmid = task['geometries']['features'][0]['properties']['osmid']
            geom = task['geometries']

            yield prepare_task(node=task,
                               args=args,
                               osmid=osmid,
                               geom=geom
                               )
        else:
            for task in tasks:
                yield task


def get_current_task_statuses(slug):
    r = requests.get(mr_api_querystatuses_endpoint.format(slug=slug))
    return dict((s['identifier'], s['status']) for s in r.json())


def generate_id(slug, osmid, payload):
    # generate a unique identifier
    payload['geometries']['features'] = \
        sorted(payload['geometries']['features'])

    digest = hashlib.md5(json.dumps(payload, sort_keys=True)).hexdigest()
    return "{slug}-{osmid}-{digest}".format(slug=slug,
                                            osmid=osmid,
                                            digest=digest
                                            )


def prepare_task(node, args, osmid, geom):
        instruction = node.get("instruction", None) or args.instruction or ''

        payload = {"instruction": instruction,
                   "geometries": geom
                   }

        identifier = node.get('id', None)

        if identifier is None:
            identifier = generate_id(slug=args.challenge_slug,
                                     osmid=osmid,
                                     payload=payload
                                     )
        return identifier, payload


def select_tasks(newtasks, oldtasks):
    for identifier, payload in newtasks:
        if identifier in oldtasks.keys():
            if oldtasks[identifier] in CFS_STATUSES:
                # if task is already there, skip it
                continue
        else:
            # new task, create it
            yield identifier, payload


def post_tasks(slug, tasks):
    # and fire!
    s = requests.session()

    task_requests = []
    newids = set()
    for identifier, payload in tasks:
        newids.add(identifier)
        task_requests.append(
            grequests.put(
                mr_api_addtask_endpoint.format(slug=slug, id=identifier),
                session=s,
                data=payload,
                headers=HEADERS))

    return grequests.map(task_requests), newids


def update_tasks(slug, tasks, instruction=None, statuses=None):
    s = requests.session()

    task_requests = []
    for identifier, payload in tasks:
        if instruction is not None:
            payload = {"instruction": instruction,
                       "geometries": payload["geometries"]
                       }

        if identifier not in statuses.keys():
            continue

        task_requests.append(
            grequests.put(
                mr_api_addtask_endpoint.format(slug=slug, id=identifier),
                session=s,
                data=payload,
                headers=HEADERS))

    return grequests.map(task_requests)


def close_tasks(slug, closeids):
    payload = {"status": "deleted"}

    s = requests.session()

    task_requests = []
    for identifier in closeids:
        task_requests.append(
            grequests.put(
                mr_api_addtask_endpoint.format(slug=slug, id=identifier),
                session=s,
                data=payload,
                headers=HEADERS))

    return grequests.map(task_requests)


def write_responses(responses, output):
    for r in responses:
        with open(output, 'a+') as outfile:
            try:
                outfile.write(str(r.json())+'\n')
            except AttributeError:
                newr = json.dumps({'identifier': r, 'status': 'failed'})
                outfile.write(str(newr+'\n'))


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
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--create',
                       default=False,
                       action='store_true',
                       help='TBW')
    group.add_argument('--close',
                       default=False,
                       action='store_true',
                       help='TBW')
    parser.add_argument('--force-post',
                        default=False,
                        action='store_true',
                        help='execute responses even with dry run set.')
    parser.add_argument('--output',
                        default='responses.json',
                        help='the output file where answer from the server, \
                        are written. \
                        Defaults to responses.json.')
    parser.add_argument('--update-instruction',
                        action='store_true',
                        default=False,
                        help='TBW')
    parser.add_argument('--update-geometries',
                        action='store_true',
                        default=False,
                        help='Enable verbose output of http requests')
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

    slug = args.challenge_slug
    # the MapROulette API endpoints
    base = args.server + "api/"
    # - for getting a challenge
    mr_api_getchallenge_endpoint = base + "challenge/{slug}"
    # - for creating a challenge
    mr_api_createchallenge_endpoint = base + "admin/challenge/{slug}"
    # - for creating a task
    mr_api_addtask_endpoint = base + "admin/challenge/{slug}/task/{id}"
    # - for quering the status off all the tasks of challenge
    mr_api_querystatuses_endpoint = base + "admin/challenge/{slug}/tasks"

    challenge_title = args.challenge_title
    if not args.challenge_title:
        challenge_title = slug

    # check if we got a running MR API instance.
    if not args.dry and not is_running_instance(base):
        print 'There is no running MapRoulette API instance at {}'.format(base)
        print 'You can supply a MR server URL with the --server option.'
        exit(0)

    # if the challenge does not exist, create it.
    if not args.dry:
        if args.close or args.update_instruction or args.update_geometries:
            assert challenge_exists(args.challenge_slug)
        else:
            create_challenge_if_not_exists(slug, challenge_title)

    statuses = {}
    if not args.dry:
        statuses = get_current_task_statuses(slug)

    tasks = []
    if 'query' in args:
        tasks = get_tasks_from_db(args)

    if 'json_file' in args:
        tasks = get_tasks_from_json(args)

    responses = []
    if not args.dry or args.force_post:
        if not (args.close or
                args.update_geometries or args.update_instruction):

            tasks = select_tasks(tasks, statuses)
            responses, newids = post_tasks(slug=slug, tasks=tasks)

            responses = [res
                         if isinstance(res, requests.models.Response)
                         else nid
                         for res, nid in zip(responses, newids)
                         ]

            write_responses(responses, args.output)

            oldids = set(old
                         for old in statuses.keys()
                         if old['status'] in CFS_STATUSES)

            closeids = oldids - newids
            responses = close_tasks(slug, closeids)

        else:
            if args.update_instruction or args.update_geometries:
                instructions = args.instruction or None
                responses = update_tasks(slug=slug,
                                         tasks=tasks,
                                         instructions=instructions,
                                         statuses=statuses
                                         )
            else:
                # args.close = True
                responses = close_tasks(slug=slug,
                                        closeids=tasks,
                                        statuses=statuses
                                        )

        write_responses(responses, args.output)

    print '\ndone.'
