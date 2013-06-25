"""This module contains the data for a GeoError, the most common type
of MapRoulette Challenge"""

from models import Challenge, challenge_types
import buttons

class Default(Challenge):
    dlg = {
        'text': "This area is being loaded in your editor.\n\nDid you fix it?",
        'buttons': [buttons.fixed, buttons.skipped]}

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
            l = [i for i in task.actions where i.status == "falsepositive" \
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
