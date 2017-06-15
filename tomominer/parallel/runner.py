import time
import os
import sys
import uuid
import logging
from multiprocessing import Process

from rpc_client import RPCClient
from task import Task



class Runner:

  def __init__(self, host, port):
    """
    Connect to the server.  Setup a logging handler so all logging events
    are sent to the server.  A new project is created for the duration of
    this objects lifecycle.

    :param host: RPCServer IP address
    :param port: RPCServer port
    """
    self.work_queue = RPCClient(host, port)

    # create a random identifier to use as a project id.
    self.proj_id = str(uuid.uuid4())
    self.work_queue.new_project(self.proj_id)

  def __del__(self):
    """
    When we are done, delete our project from the remove server, so it will
    not hold any more jobs or results on the server.
    """
    self.work_queue.del_project(self.proj_id)
    del self.work_queue

  def make_task(self, method, *args, **kwargs):

    return Task(self.proj_id, method, *args, **kwargs)

  def run_single(self, task, max_time=3600, max_retry=1):
    """
    Run a single task.

    """

    tries = 1

    while tries <= max_retry:

      tries += 1
      self.work_queue.put_task(task)

      while True:
        results = self.work_queue.get_results(self.proj_id)

        # If the job is not complete, wait and try again.
        if not results:
          time.sleep(1)
          logging.debug("run_single: No results yet")
          continue

        # Otherwise we should have a list with a single element.  The
        # result we are waiting on.
        for res in results:
          if res.task_id != task.task_id:
            logging.warn("run_single got the wrong task back: %s", res)
            continue
          if res.error:
            if tries >= max_retry:
              raise Exception(res.error_msg)
          else:
            logging.debug("run_single: returning %s", res)
            return res
        time.sleep(1)

    raise Exception("run_single: should never reach this point")


  def run_batch(self, tasks, max_time=3600, max_retry=1):
    """
    Run a number of tasks by submitting to the QueueServer for processing
    by QueueWorker processes.

    :param tasks:    The list of Task() objects to submit.
    :param max_time:   Currently unused.
    :param max_retry:  Number of times to attempt the function call in the
              event of an error being returned, or a timeout occuring.
    """

    task_dict = {}
    """ A mapping from task_id to Task objects. """

    state   = {}
    """Track the number of times remaining that we will try to submit this job.  When this reaches zero, on a failure we will throw an exception.  Until then we retry the whole task."""

    for t in tasks:
      t.max_time = max_time
      task_dict[t.task_id] = t
      state[t.task_id] = max_retry
      logging.debug("sending task %s to queue", (t.task_id,t.method))
    self.work_queue.put_tasks(tasks)

    while len(state):
      logging.debug("%s tasks out to workers", len(state))

      results = self.work_queue.get_results(self.proj_id)

      for res in results:

        if res.task_id not in state:
          # from a previous run that got cancelled?
          # or a timed out job?
          logging.warning("recieved result from an unknown task: %s", (res,))
          continue

        # What to do in case of an error running a task.
        if res.error:
          logging.error("result %s, contains error flag.  task raised exception remotely: %s", res.task_id, res)
          logging.error("error in result %s:", (dict(proj_id = res.proj_id, task_id = res.task_id, method=res.method, args = res.args, kwargs = res.kwargs, result = res.result, error = res.error),))
          # Reduce the number of times we will rerun it.
          state[res.task_id] -= 1
          # Resubmit the task if we are allowed to retry.
          if state[res.task_id] > 0:
            logging.warning("resubmitting crashed task: %s", res.task_id)
            self.work_queue.put_task(task_dict[res.task_id])
          else:
            # Panic!  The task failed, and we have retried the maximum number of times.  So we exit.
            logging.error("task failed too many times: %s", res)
            raise Exception

        # iterate over the results.
        del state[res.task_id]
        yield res


      time.sleep(1)


if __name__ == '__main__':

  r = Runner('127.0.0.1', 5011)
  r.run_single('echo', "testing")
  res = r.run_single('reverser', "testing")
  print res.result
