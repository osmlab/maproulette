"""Some helper functions"""
from flask import abort
from maproulette.models import Challenge, Task

def get_challenge_or_404(slug, instance_type=None):
    """Return a challenge by its slug or return 404.

    If instnance_type is True, return the correct Challenge Type
    """
    c = Challenge.query.filter(Challenge.slug==slug).first_or_404()
    if not c.active:
        abort(503)
    if instance_type:
        return challenge_types[c.type].query.get(c.id)
    else:
        return c

def get_task_or_404(challenge_slug, task_identifier):
    """Return a task based on its challenge slug and task identifier"""
    c = get_challenge_or_404(challenge_slug)
    t = Task.query.filter(Task.identifier==task_identifier).\
        filter(Task.challenge_id==c.id).first_or_404()
    return t
