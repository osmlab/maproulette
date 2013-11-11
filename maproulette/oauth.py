#!/usr/bin/env python

import json  # @UnusedImport
from maproulette import app, models
from flask_oauthlib.client import OAuth
from flask import request, url_for, redirect, session
from flask.ext.sqlalchemy import SQLAlchemy
from maproulette.database import db
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape

# instantiate OAuth object
oauth = OAuth()
osm = oauth.remote_app(
    'osm',
    app_key = 'OSM'
)
oauth.init_app(app)

@osm.tokengetter
def get_osm_token(token=None):
#    session.regenerate() this should be done elsewhere.
    if 'osm_oauth' in session:
        resp = session['osm_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']

@app.route('/login')
def oauth_authorize():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return osm.authorize(callback=callback_url or request.referrer or None)

@app.route('/oauthorized')
@osm.authorized_handler
def oauthorized(resp):
    """Receives the OAuth callback from OSM"""
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        return redirect(next_url)
    session['osm_oauth'] = resp
    retrieve_osm_data()
    app.logger.debug('redirecting to %s' % next_url)
    return redirect(next_url)

def retrieve_osm_data():
    data = osm.get('user/details').data
    app.logger.debug("getting user data from osm")
    if not data:
        # FIXME this requires handling
        return False
    userxml = data.find('user')
    osmid = userxml.attrib['id']
    # query for existing user
    if bool(models.User.query.filter(models.User.id==osmid).count()):
        app.logger.debug('user exists, getting from database')
        user = models.User.query.filter(models.User.id==osmid).first()
    else:
        app.logger.debug('user is new, create local account')
        user = models.User()
        user.id = osmid
        user.display_name = userxml.attrib['display_name']
        user.osm_account_created = userxml.attrib['account_created']
        homexml = userxml.find('home')
        if homexml is not None:
            user.home_location = WKTElement('POINT(%s %s)' % (homexml.attrib['lon'], homexml.attrib['lat']))
        else:
            app.logger.debug('no home for this user')
        languages = userxml.find('languages')
        #FIXME parse languages and add to user.languages string field
        user.changeset_count = userxml.find('changesets').attrib['count']
        # get last changeset info
        changesetdata = osm.get('changesets?user=%s' % (user.id)).data
        try:
            lastchangeset = changesetdata.find('changeset')
            if 'min_lon' in lastchangeset.attrib:
                wktbbox = 'POLYGON((%s %s, %s %s, %s %s, %s %s, %s %s))' % (
                        lastchangeset.attrib['min_lon'],
                        lastchangeset.attrib['min_lat'],
                        lastchangeset.attrib['min_lon'],
                        lastchangeset.attrib['max_lat'],
                        lastchangeset.attrib['max_lon'],
                        lastchangeset.attrib['max_lat'],
                        lastchangeset.attrib['max_lon'],
                        lastchangeset.attrib['min_lat'],
                        lastchangeset.attrib['min_lon'],
                        lastchangeset.attrib['min_lat'])
                app.logger.debug(wktbbox)
                user.last_changeset_bbox = WKTElement(wktbbox)
                user.last_changeset_date = lastchangeset.attrib['created_at']
                user.last_changeset_id = lastchangeset.attrib['id']
        except:
            app.logger.debug('could not get changeset data from OSM')
        db.session.add(user)
        db.session.commit()
        app.logger.debug('user created')
    # we need to convert the GeoAlchemy object to something picklable
    if user.home_location is not None:
        point = to_shape(user.home_location)
        session['home_location'] = [point.x, point.y] or None
    session['display_name'] = user.display_name
    session['osm_id'] = user.id
    session['difficulty'] = user.difficulty
