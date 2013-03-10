#!/usr/bin/env python

import os

secret = os.urandom(24).encode('hex')

fd = open('settings.py', 'w')
fd.write("""
secret_key = "%(secret)s"
""" % { 'secret': secret})
