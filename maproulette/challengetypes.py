"""This module contains the various challenge types"""

from maproulette.models import Challenge
from flask_restful import fields

challenge_types = {}

# The default challenge type. Other challenge types should
# inherit from this.


class Default(Challenge):
    """The default challenge class"""

    # the allowed actions for this challenge type, and whether they
    # represent the task being available or not
    def actions():
        return {
            'created': True,
            'available': True,
            'skipped': True,
            'assigned': False,
            'falsepositive': False,
            'fixed': False,
            'deleted': False
        }

    done_dialog_text = "This area is being loaded in your editor. \
        Did you fix it?"
    # an empty string will trigger the default buttons.
    done_dialog_buttons = ""

    marshal_fields = {
        'slug': fields.String,
        'title': fields.String,
        'description': fields.String,
        'blurb': fields.String,
        'help': fields.String,
        'instruction': fields.String,
        'active': fields.Boolean,
        'difficulty': fields.Integer
    }

    marshal_fields['done_dlg'] = {}
    marshal_fields['done_dlg']['text'] = fields.String(
        attribute='done_dialog_text')
    marshal_fields['done_dlg']['buttons'] = fields.String(
        attribute='done_dialog_buttons')

# Now register this class with the Challenge
challenge_types['default'] = Default
