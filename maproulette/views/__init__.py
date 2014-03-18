"""The various views and routes for MapRoulette"""

from flask import render_template, redirect, session
from maproulette import app
from maproulette.helpers import signed_in

from maproulette.models import User, Challenge, Task, TaskGeometry, Action, db
from flask import Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.sqlalchemy import SQLAlchemy
from wtforms.fields import SelectField, TextAreaField

class ChallengeAdminView(ModelView):
    column_list = ('slug', 'title', 'blurb')
    form_overrides = dict(difficulty=SelectField,
                          help=TextAreaField)
    form_args = dict(
        difficulty=dict(
            choices=[ (1, 'Beginner'), (2, 'Intermediate'), (3, 'Advanced')]),
        )
    form_widget_args = dict(
        help = dict(rows="20", cols="200")
        )
    def __init__(self, session, **kwargs):
        super(ChallengeAdminView, self).__init__(Challenge, session, **kwargs)

class TaskAdminView(ModelView):
    def __init__(self, session, **kwargs):
        super(TaskAdminView, self).__init__(Task, session, **kwargs)

admin = Admin(app, name="MapRoulette")
admin.add_view(ChallengeAdminView(db.session))        
admin.add_view(TaskAdminView(db.session))

@app.route('/')
def index():
    """Display the main page"""
    if app.config["TEASER"]:
        return render_template('teaser.html')
    else:
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
