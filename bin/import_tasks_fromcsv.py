#!/usr/bin/env python

# a script to load a CSV file into the MapRoulette tasks table.
# this script takes four arguments:
# 1. path to input file (csv)
# 2. prefix for task identifier
# 3. challenge id
# 4. run number
# assumes a comma separated file with the osm id as the first
# field, the location as WKT point as the second field, and a
# thrid field containing a string descriptor which will be loaded
# to the manifest field
#
# use with sample data in this directory:
#
# python import_tasks_fromcsv.py sampledata.csv sample 1 1


import csv, json, os, sys, psycopg2

dbhost = 'localhost'
dbport = '5432'
dbname = 'maproulette'
dbuser = 'osm'
dbpass = 'osm'
cnt = 0

if __name__ == "__main__":
    if not len(sys.argv) == 5:
        print "needs four arguments"
        sys.exit(1)
    infile = sys.argv[1]
    prefix = sys.argv[2]
    challenge_id = sys.argv[3]
    run_id = sys.argv[4]
    if not os.path.isfile(infile):
        print "%s is not a file" % (infile)
        sys.exit(2)
    elif len(prefix) > 30:
        print "prefix too long, must be 30 chars or less"
    conn = psycopg2.connect(
        "host=%s port=%s dbname=%s user=%s password=%s" % 
        (dbhost, dbport, dbname, dbuser, dbpass))
    cur = conn.cursor()
    # check for challenge
    cur.execute('SELECT id FROM challenges WHERE id = %s', (challenge_id))
    c = cur.fetchall()
    if c is None:
        print "challenge %s does not exist, please create it first" % (challenge_id)
        exit(1)
    sqlstub = "INSERT INTO tasks (identifier, location, manifest, challenge_id, run) VALUES (%s, ST_GeomFromText(%s), %s, %s, %s)"
    with open(infile, 'rb') as f:
        r = csv.reader(f)
        for row in r:
            if len(row) != 3:
                continue
            cur.execute(sqlstub, (prefix + "_" + row[0], row[1], row[2], challenge_id, run_id))
            cnt += 1
    conn.commit()
    cur.close()
    conn.close()
    print "done. %i tasks added for challenge_id %s" % (cnt, challenge_id,)
