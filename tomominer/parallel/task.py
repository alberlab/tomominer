import uuid
import time

class Task(object):
  """
  An object representing a work unit.  Each task has a unique identifier
  (task_id) which is randomly generated and is used to tracking the task
  throughout it's lifecycle.

  There is another unique identifier the proj_id (project_id) which
  identifies the project which created the task, and is used by the server to
  map tasks to the master processes which requested them.
  """

  def __init__(self, proj_id, method, allow_resubmit=True, max_tries=3, max_time=3600, burst=0, args=(), kwargs={}):
    """
    Generate a new Task object.  This will run: method(*args, **kwargs) and
    return the result to the project identified by proj_id, when submitted
    to the work server.

    :param proj_id: The project requesting the work.
    :param method:  Function to run in the QueueWorker instance.
    :param args:  Arguments for the function
    :param kwargs:  Keyword arguments from the function
    """

    if not isinstance(max_time, int) or max_time < 0:
      raise Exception("Max time must be a positive integer")

    self.proj_id = proj_id

    # generate a random identifier for this task.
    self.task_id = str(uuid.uuid4())
    """ A random identifier for the task. """

    self.method  = method
    self.args  = args
    self.kwargs  = kwargs

    self.allow_resubmit = allow_resubmit
    """ True if the Task is independent enough that two versions can run.  """

    self.max_tries = max_tries
    """ Number of times to try and run the function on error. Currently
    unused."""

    self.max_time  = max_time
    """ Maximum amount of time to let the function run before assuming it
    crashed or was otherwise lost.  """

    self.burst  = burst
    """If we are allowed to start multiple cases at the same time.  How
    many to launch in quick succession.  This may not be honored by the
    server depending on traffic, and available resources"""

    self.tries   = 0
    """ Number of times we have already attempted to run this Task. """

    self.result  = None
    """ The result of the method call """

    self.error   = False
    """ True if an Exception is thrown, or this variable is simply set
    during the function call"""

    # TODO expand this into a traceback object that is sent back.

    self.todo_queue_total   = None
    """ Total time spent in the server.todo_queue waiting for a worker
    process.  None if not submitted, or still in the todo_queue. """

    self.calc_total     = None
    """ Total time used calculating the method.  This is according to the
    server, and should be not be used for timing or benchmarking. """

    self.done_queue_total   = None
    """ Total time spent waiting for the project owner to pick up finished
    tasks.  """

  def fail(self, msg=""):
    """
    This function is called in the event of an error or an exception, with
    a message explaining the issue that caused the Task to fail.
    """
    self.error  = True
    self.result = msg

  def succ(self, res):
    """
    Called when the Task successfully completes the given method call.  The
    result is stored with the task.
    """
    self.error  = False
    self.result = res

  def __repr__(self):
    return "Task( proj_id = %s, task_id = %s,  method = %s, error = %s, result = %s )" % (self.proj_id[:8], self.task_id[:8], self.method, self.error, self.result)
