#!/usr/bin/env python

import os

secret = os.urandom(24).encode('hex')

fd = open('secret.cfg', 'w')
fd.write("""
SECRET_KEY = "%(secret)s"
""" % {'secret': secret})
