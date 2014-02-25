#!/usr/bin/env python

import json
import sys
import requests

challenge_id = sys.argv[1]
old_fname = sys.argv[2]
cur_fname = sys.argv[3]

r = requests.get('http://localhost:8866/api/admin/challenge/%s/tasks' % challenge_id)
r.raise_for_status()

statuses_raw = r.json()
statuses = {i['id']: i['status'] for i in statuses_raw}

old = {i['id']: i for i in json.loads(open(old_fname, 'r').read())}
new = {i['id']: i for i in json.loads(open(new_fname, 'r').read())}

# First, we'll remove any false positives from either the new or old list
old_ids = Set([i for i in old if statuses.get(i) != 'false_positive'])
new_ids = Set([i for i in cur if statuses.get(i) != 'false_positive'] and i not in old)

# Now figure out what's old, what's new and what's changed
deleted_ids = cur_ids.difference(new_ids)
new_ids = new_ids.difference(cur_ids)
changed_ids = [i for in in old_ids.intersection(new_ids) if old[i] != new[i]]

# Output stats here, and optional "do not do"

# In order of priority, delete old task, update tasks and add tasks
for i in deleted_ids:
    print "Deleting %s... ", % i
    requests.delete('http://localhost:8866/api/admin/challenge/%s/task/%s' %
                    challenge_id, i)
    r.raise_for_status()
    print "Done"
    
for i in changed_ids:
    print "Uploading changed %s...", % i
    requests.put('http://localhost:8886/api/admin/challenge/%s/task/%s' %
                 challenge_id, i,
                 headers = {'Content-type': 'application/json',
                            'Accept': 'text/plain'},
                 payload = json.dump(new[i]))
    r.raise_for_status()
    print "Done"

for i in to_new_ids:
    print "Uploading new %s...", % i
    requests.put('http://localhost:8866/api/admin/challenge/%s/task/%s' %
                 challenge_id, i, payload = json.dumps(new[i]),
                 headers = {'Content-type': 'application/json',
                            'Accept': 'text/plain'},
                 payload = json.dumps(new[i]))
    r.raise_for_status()
    print "Done"

                 
