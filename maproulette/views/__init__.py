"""The various views and routes for MapRoulette"""

from flask import render_template, redirect, session
from maproulette import app

# By default, send out the standard client

@app.route('/')
def index():
    "Display the index.html"
    return render_template('index.html')


@app.route('/logout')
def logout():
    # make sure we're authenticated
    if 'osm_token' in session or app.debug:
        session.destroy()
    return redirect('/')
