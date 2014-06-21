#!/usr/bin/env python

import hashlib
import psycopg2
import getpass
import simplejson
import requests
import grequests
import geojson
import json
import argparse
import logging
from shapely import wkb
from psycopg2.extras import register_hstore, DictCursor


CFS_STATUSES = ('created', 'falsepositive', 'skipped')

CLOSING_PAYLOAD = json.dumps({"status": "closed"})


DELETING_PAYLOAD = json.dumps({"status": "deleted"})

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
    else:
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
        osmid = task['geometries']['features'][0]['properties']['osmid']
        geom = task['geometries']

        yield prepare_task(node=task,
                           args=args,
                           osmid=osmid,
                           geom=geom
                           )


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

        payload = json.dumps(payload)

        return identifier, payload


class Requester(object):

    def __init__(self, sync=False):
        self.sync = sync

    def __enter__(self):
        if self.sync:
            self.responses = []

        else:
            self.session = requests.session()

            self.task_requests = []

        return self

    def __exit__(self, type, value, traceback):
        pass

    def request(self, url, payload):
        if self.sync:
            self.responses.append(
                requests.put(url,
                             data=payload,
                             headers=HEADERS
                             ))
        else:
            self.task_requests.append(
                grequests.put(url,
                              session=self.session,
                              data=payload,
                              headers=HEADERS
                              ))

    def finish(self):
        if self.sync:
            return self.responses
        else:
            return grequests.map(self.task_requests, size=50)


def select_tasks(newtasks, oldtasks):
    for identifier, payload in newtasks:
        if identifier in oldtasks.keys():
            if oldtasks[identifier] in CFS_STATUSES:
                # if task is already there, skip it
                continue
        else:
            # new task, create it
            yield identifier, payload


def post_tasks(slug, tasks, sync):
    newids = set()

    with Requester(sync) as req:
        for identifier, payload in tasks:
            newids.add(identifier)
            url = mr_api_addtask_endpoint.format(slug=slug, id=identifier)
            req.request(url=url, payload=payload)

        responses = req.finish()

    return responses, newids


def update_tasks(slug, tasks, instruction=None, statuses=None, sync=False):
    updids = set()

    with Requester(sync) as req:
        for identifier, payload in tasks:
            if identifier not in statuses.keys():
                continue

            if instruction is not None:
                payload = {"instruction": instruction,
                           "geometries": payload["geometries"]
                           }

            updids.add(identifier)
            url = mr_api_addtask_endpoint.format(slug=slug, id=identifier)
            req.request(url=url, payload=payload)

        responses = req.finish()

    return responses, updids


def close_tasks_by_id(slug, closeids, sync=False):
    closeids = set()

    with Requester(sync) as req:
        for identifier in closeids:
            closeids.add(identifier)
            url = mr_api_addtask_endpoint.format(slug=slug, id=identifier)
            req.request(url=url, payload=CLOSING_PAYLOAD)

        responses = req.finish()

    return responses, closeids


def delete_tasks(slug, tasks, statuses, sync=False):
    delids = set()

    with Requester(sync) as req:
        for identifier, orig_p in tasks:

            if identifier not in statuses.keys():
                continue

            delids.add(identifier)
            url = mr_api_addtask_endpoint.format(slug=slug, id=identifier)
            req.request(url=url, payload=DELETING_PAYLOAD)

        responses = req.finish()

    return responses, delids


def write_responses(responses, output):
    for res, nid in responses:
        with open(output, 'a+') as outfile:
            try:
                outfile.write(str(res.json())+'\n')

            except AttributeError:
                newr = json.dumps({'identifier': nid,
                                   'status': 'failed'
                                   }
                                  )
                outfile.write(str(newr+'\n'))

            except simplejson.scanner.JSONDecodeError:
                newr = json.dumps({'identifier': nid,
                                   'status': res.status_code
                                   }
                                  )
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
    group.add_argument('--delete',
                       default=False,
                       action='store_true',
                       help='Set status of tasks to "deleted"')
    parser.add_argument('--force-post',
                        default=False,
                        action='store_true',
                        help='Post tasks even with dry run set.')
    parser.add_argument('--output',
                        default='responses.json',
                        help='the output file where answer from the server, \
                        are written. \
                        Defaults to responses.json.')
    parser.add_argument('--update-instruction',
                        action='store_true',
                        default=False,
                        help='Update challenge instruction')
    parser.add_argument('--update-geometries',
                        action='store_true',
                        default=False,
                        help='Update geometries of task')
    parser.add_argument('-v', '--verbose',
                        default=False,
                        action='store_true',
                        help='Enable verbose output of http requests')
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help='Enable debugging output of http requests')
    parser.add_argument('--no-close',
                        default=False,
                        action='store_true',
                        help='Do not close the statuses')
    parser.add_argument('--sync',
                        default=False,
                        action='store_true',
                        help='Make only synchronous requests')

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

    if not args.server.endswith('/'):
        raise ValueError('Server name must have a trailing slash')

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
        if args.delete or args.update_instruction or args.update_geometries:
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
        if not (args.delete or
                args.update_geometries or args.update_instruction):

            all_tasks = [t for t in tasks]
            rimids = set([nid for nid, p in all_tasks])

            tasks_to_post = select_tasks(all_tasks, statuses)
            responses, newids = post_tasks(
                slug=slug,
                tasks=tasks_to_post,
                sync=args.sync)

            responses = [(res, nid)
                         for res, nid in zip(responses, newids)
                         ]

            write_responses(responses, args.output)

            oldids = set(old
                         for old in statuses.keys()
                         if statuses[old] in CFS_STATUSES)

            if not args.no_close:
                closeids = oldids - newids - rimids
                responses, cloids = close_tasks_by_id(slug, closeids)

                responses = [(res, cid)
                             for res, cid in zip(responses, cloids)
                             ]

        else:
            if args.update_instruction or args.update_geometries:
                instructions = args.instruction or None
                responses, updids = update_tasks(slug=slug,
                                                 tasks=tasks,
                                                 instructions=instructions,
                                                 statuses=statuses,
                                                 sync=args.sync
                                                 )

                responses = [(res, uid)
                             for res, uid in zip(responses, updids)
                             ]

            else:
                # args.delete = True
                responses, delids = delete_tasks(slug=slug,
                                                 tasks=tasks,
                                                 statuses=statuses,
                                                 sync=args.sync
                                                 )
                responses = [(res, did)
                             for res, did in zip(responses, delids)
                             ]

        write_responses(responses, args.output)

    print '\ndone.'
