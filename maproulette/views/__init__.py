"""The various views and routes for MapRoulette"""

from flask import render_template, redirect, session
from maproulette import app
from maproulette.helpers import signed_in

from maproulette.models import Challenge, Task, db

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logout')
def logout():
    if signed_in() or app.debug:
        session.destroy()
    return redirect('/')
