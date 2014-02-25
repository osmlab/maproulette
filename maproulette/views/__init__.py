"""The various views and routes for MapRoulette"""

from flask import render_template, redirect, session
from maproulette import app
from maproulette.helpers import signed_in


@app.route('/')
def index():
    """Display the main page"""
    return render_template('index.html')


@app.route('/logout')
def logout():
    if signed_in() or app.debug:
        session.destroy()
    return redirect('/')


@app.route('/me')
def me():
    """Display a page about me with some stats
    and user settings."""
    return render_template('me.html')


@app.route('/stats/<challenge_slug>')
def challenge_stats(challenge_slug):
    """Display a page about me with some stats
    and user settings."""
    return render_template('stats.html', challenge_slug=challenge_slug)
