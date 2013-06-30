#!/usr/bin/python

# this script takes two arguments:
# 1. path to input file (csv)
# 2. prefix for task identifier
# assumes a comma separated file with the osm
# 
import csv, json, os, sys

if __name__ == "__main__":
    if not len(sys.argv) == 3:
        print "needs two arguments"
        sys.exit(1)
    elif not os.path.isfile(sys.argv[1]):
        print "%s is not a file" % (sys.argv[1])
        sys.exit(2)
    elif len(sys.argv[2]) > 30:
        print "prefix too long, must be 30 chars or less"
    with open(sys.argv[1], 'rb') as f:
        with open('/osm/out/utahnourl.json', 'wb') as o:
            r = csv.reader(f)
            l = []
            i = 0
            for row in r:
                row.insert(0, sys.argv[2] + row[i])
                l.append(row)
            o.write(json.dumps(l))
        
