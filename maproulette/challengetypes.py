"""This module contains the various challenge types"""

from maproulette.models import Challenge
import maproulette.buttons as buttons
from flask.ext.restful import fields

challenge_types = {}

# The default challenge type. Other challenge types should
# inherit from this.


class Default(Challenge):

    done_dialog_text = "This area is being loaded in your editor. Did you fix it?"
    done_dialog_buttons = "" # an empty string will trigger the default buttons.

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

    @property
    def task_status(self, task):
        current_state = task.current_action.state
        if current_state == 'created' or current_state == 'modified':
            return 'available'
        elif current_state == 'skipped':
            return 'available'
        elif current_state == 'fixed':
            return 'done'
        elif (current.status == 'alreadyfixed' or
              current.status == 'falsepositive'):
            l = [i for i in task.actions if i.status == "falsepositive"
                 or i.status == "alreadyfixed"]
            if len(l) >= 2:
                return 'done'
            else:
                return 'available'
        else:
            # A TASK SHOULD NEVER GET HERE- if it does, it's due to
            # some illegal action. Throw the task back on the work pile
            return 'available'

    @task_status.setter
    def set_task_status(self, task):
        current = task.current
        if current.status == 'skipped':
            task.setavailable()
        elif current.status == 'fixed':
            task.setdone()
        elif (current.status == 'alreadyfixed'
              or current.status == 'falsepositive'):
            # We should see two of these before setting the task to done
            l = [i for i in task.actions if i.status == "falsepositive"
                 or i.status == "alreadyfixed"]
            if len(l) >= 2:
                task.setdone()
            else:
                task.setavailble()
        else:
            # A TASK SHOULD NEVER GET HERE- if it does, it's due to
            # some illegal action. Throw the task back on the work pile
            task.setavailable()

# Now register this class with the Challenge
challenge_types['default'] = Default
