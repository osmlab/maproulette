#!/usr/bin/env python

"""This program converts the maproulette-front config files (settings.py and config.ini) into a supervisor compatible config file.

This should be run each time the settings.py or the config.ini file are modified
"""

from ConfigParser import ConfigParser
from StringIO import StringIO
from shutil import copyfileobj

frontmatter_fname = "supervisord_front.conf"
frontmatter = open(frontmatter_fname, 'r')

mr_config = ConfigParser({'command': 'app.py'})
mr_config.read('config.ini')

out_config = ConfigParser()

for challenge in mr_config.sections():
    command = mr_config.get(challenge, 'command')
    port = mr_config.get(challenge, 'port')
    # Now store the section
    program = "program:" + challenge
    out_config.add_section(program)
    out_config.set(program, "command", command)

# Store the config in a dummy object
mr_config_out = StringIO()
out_config.write(mr_config_out)

# Write it out
out_fh = open("supervisord.conf", 'w')
copyfileobj(frontmatter, out_fh)
copyfileobj(mr_config_out, out_fh)
out_fh.close()

