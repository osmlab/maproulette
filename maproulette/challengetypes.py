"""This module contains the various challenge types"""

from maproulette.models import Challenge
import maproulette.buttons as buttons
from flask.ext.restful import fields

challenge_types = {}

# The default challenge type. Other challenge types should
# inherit from this.

class Default(Challenge):
    """The default challenge class"""

    done_dialog_text = "This area is being loaded in your editor. Did you fix it?"
    done_dialog_buttons = ""  # an empty string will trigger the default buttons.

    marshal_fields = {
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
