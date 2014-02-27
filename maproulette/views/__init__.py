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


@app.route('/challenge/<challenge_slug>')
def challenge_page(challenge_slug):
    """Display a page about me with some stats
    and user settings."""
    return render_template('challenge.html', challenge_slug=challenge_slug)


@app.route('/challenge_stats')
def challenge_stats():
    """Display the summary stats for all challenge_stats"""
    return render_template('challenges.html')
