"""This module contains the various challenge types"""

from maproulette.models import Challenge, challenge_types
import maproulette.buttons as buttons

challenge_types = {}

class Default(Challenge):
    self.done_dlg = {
        'text': "This area is being loaded in your editor.\n\nDid you fix it?",
        'buttons': [buttons.fixed, buttons.skipped]}
    
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
            l = [i for i in task.actions if i.status == "falsepositive" \
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
            l = [i for i in task.actions if i.status == "falsepositive" \
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
challenge_types['Default'] = Default
