#!/usr/bin/env python

# This sets tasks that have been 'assigned' for more than
# a given timespan back to 'available'.
# This should be run as a cron job at an interval coinciding
# with the timespan defined in stale_threshold.

from maproulette.models import db, Task, Action
from sqlalchemy.sql.functions import max
from datetime import datetime, timedelta
import pytz

current_time = datetime.now(pytz.utc)
stale_threshold = current_time - timedelta(hours=1)


def get_stale_assigned_tasks():
    """returns all assigned tasks that are stale"""

    # select t.id from tasks t, actions a where
    # a.task_id = t.id and t.currentaction = 'assigned'
    # group by t.id having now() - max(a.timestamp) < interval '1 day';
    return db.session.query(Task).filter(
        Task.currentaction.in_(['assigned', 'editing'])).join(
        Task.actions).group_by(
        Task.id).having(max(Action.timestamp) < stale_threshold).all()

if __name__ == "__main__":
    counter = 0
    for task in get_stale_assigned_tasks():
        task.append_action(Action("available"))
        db.session.add(task)
        print "setting task %s to available" % (task.identifier)
        counter += 1
    db.session.commit()
    print 'done. %i tasks made available' % counter
