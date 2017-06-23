import os
import sys
import time
import threading
import traceback
import Queue
from collections import defaultdict
import itertools
import logging

#import logging.handlers
from task import Task

def now():
    return time.time()

class max_time_monitor(threading.Thread):

  def __init__(self, server, interval):
    threading.Thread.__init__(self)
    self.finished = threading.Event()
    self.interval = interval
    self.server   = server

  def cancel(self):
    self.finished.set()

  def run(self):
    """
    Pop next task to timeout off of the tracking priority queue.  If the
    task has been out too long, we put the job in
    the done_queue.  Only add a task to this queue if it is the last run.
    """

    while not self.finished.is_set():

      with self.server.lock:
        while True:
          try:
            max_time, task_id = self.server.max_time_queue.get_nowait()
            if now() < max_time:
              self.server.max_time_queue.put((max_time, task_id))
              logging.info("max_time_queue_thread:"
                           " Next timeout is in the future.")
              break
            else:
              if task_id not in self.server.tasks:
                logging.debug("max_time_queue_thread:"
                              " task %s not in server.tasks.", task_id)
                continue
              task = self.server.tasks[task_id]

              if task.proj_id not in self.server.done_queues:
                logging.debug("max_time_queue_thread: proj_id %s not"
                              " in server.done_queues", task.proj_id)
                continue

              # mark it as timed out.
              task.fail("Task exceeded max_time")
              self.server.done_queues[task.proj_id].put(task)
              del self.server.tasks[task_id]
              logging.debug("max_time_queue_thread: Killing task %s!", task_id)
          except Queue.Empty:
            break
      logging.info("max_time_queue_thread: sleeping.")
      self.finished.wait(self.interval)


class QueueServer:
  """

  This object is exposed by the RPCServer() as an instance.  It is a task-queue
  for  running work across a cluster of machines.  Any process with work to be
  done can connect with a project_id, and submit work to be completed.  When
  the work is done it can be retrieved using the same project_id.

  Jobs are submitted from managers to this server.  The jobs are pulled and
  processed by workers, who return any results upon completion for the managers
  to retrieve.

  Managers have two primary functions available:
    put_task()
    get_result()

  Workers have two primary functions available:
    get_task()
    put_result()

  Within the manager, the tasks flow as follows.

  put_task(task): Add task to the self.todo_queue().

  get_task():  Pop a task from self.todo_queue(). Send a copy of the task to
  the worker.

  put_result(res):  The worker returns a (error, result) object
  containing output for task.  The completed task is placed in
  self.done_queues[project_id] to be picked up.

  get_results():  All entries from the done_queues for the associated project
  are passed back.  They are removed from the done_queue.
  """

  def __init__(self, timeout_thread_interval=30, get_task_timeout=30):
    """
    Setup the QueueServer for task processing.
    """

    self.get_task_timeout = get_task_timeout

    self.todo_queue  = Queue.PriorityQueue()
    """ All work to be done is placed into this queue.  This is where work
      is pulled by workers"""

    self.lock = threading.Lock()
    """ Access to the internal structures from multiple threads is
      coordinated with a Lock()"""

    self.done_queues = {}

    """ Each completed job is put in queue for the particular project.
      This allows each project to pick up work whenever ready."""

    self.tasks = {}
    """ Cache for tasks currently out to workers."""

    self.max_time_queue = Queue.PriorityQueue()
    """ Data on when tasks will expire.  Each task with a max_time is added
      when it is returned to a worker.  If it exceeds max_time, the task
      will be recorded as a failure and placed in done_queues. """

    # The thread which monitors max_time_queue.
    self.monitor = max_time_monitor(self, timeout_thread_interval)
    self.monitor.daemon = True
    self.monitor.start()

  def __del__(self):
    self.monitor.cancel()
    self.monitor.join(timeout=1)

  def new_project(self, proj_id):
    """
    Create a new project with the given project id.  All jobs submitted
    will have an associated project_id which is used to coordinate
    ownership of jobs and results.  This allows multiple users to use the
    same server, and pool of workers.


    :param proj_id: The id of the project that is being created.
    """

    with self.lock:
      self.done_queues[proj_id] = Queue.Queue()
    logging.debug("new_project %s", proj_id)


  def del_project(self, proj_id):
    """
    Mark a project as complete.  This will clean up the project data
    structures and help mark any outstanding work as done.

    If the project is not known to the server, this will return False.

    :param proj_id: The project id to delete.
    """

    logging.debug("del_project %s", proj_id)
    with self.lock:
      if proj_id in self.done_queues:
        del self.done_queues[proj_id]
        return True
      return False


  def stats(self):
    """
    """
    return dict(active_connections=self.active_connections,
                waiting=self.todo_queue.qsize(),
                num_projects=len(self.done_queues),
                waiting_for_pickup=sum(_.qsize() for _ in self.done_queues.values()),
                num_running=len(self.tasks))


  def dump(self):
    """
    Dump several internal data structures for an external monitor.  Very
    expensive, call infrequently
    """
    raise NotImplementedError


  def put_tasks(self, tasks):
    """
    Send a group of tasks to the queue server.  This is faster then
    submitting tasks individually.

    :param tasks: A list of tasks to be added of type Task()
    """
    with self.lock:
      for task in tasks:
        if not isinstance(task.max_time, int) or task.max_time < 0:
          raise Exception("All tasks must have a valid (integer > 0) max_time")
        self.tasks[task.task_id] = task
        self.todo_queue.put((now(), task.task_id))
        logging.debug("put_task %s", task)


  def put_task(self, task):
    """
    Add a task.

    This will put the task in the queue and will run it when the resources
    are available.

    :param task: This must be an instance of a Task object.  The server
          will make assumptions about internal fields.

    :todo: perform type checking on task object.
    """
    with self.lock:
      if not isinstance(task.max_time, int) or task.max_time < 0:
        raise Exception("All tasks must have a valid (integer > 0) max_time")
      self.tasks[task.task_id] = task
      self.todo_queue.put((now(), task.task_id))
      logging.debug("put_task %s", task)


  def cancel_task(self, task_id):
    """
    :param task: The task to cancel

    :returns: True if the task was still known to the server.
    """

    with self.lock:
      if task_id in self.tasks:
        del self.tasks[task_id]
        logging.debug("cancel_task %s", task_id)
        return True
      logging.warning("cancel_task %s, not found.", task_id)
      return False


  def get_state(self, proj_id, task_id):
    """
    :param task_id:  task_id of the target task

    :returns: True if the task is queued or running.  False if crashed, done,
    or otherwise unknown

    :todo: modify so we can call get_state(proj, None) to get info on project?
    :todo: make proj_id unnecessary?
    """

    # TODO: make this useful again.  Add a self.running set to track
    # currently running processes.

    with self.lock:
      if proj_id not in self.done_queues:
        return False
      if task_id in self.tasks:
        return True
      return False


  def get_task(self, timeout=None):
    """
    Pop a task from the todo_queue, and send it out to be completed.  This
    function is called by idle workers looking for work.

    :returns: A task to be completed.
    """

    if timeout is None:
      timeout = self.get_task_timeout

    while True:
      try:
        start_time, task_id = self.todo_queue.get(timeout=timeout)

        with self.lock:

          if task_id not in self.tasks:
            logging.debug("get_task: Not sending task,"
                          " since not in self.tasks. %s", task_id)
            continue

          task = self.tasks[task_id]

          # If the project the task belongs to has already been deleted skip
          # it.
          if task.proj_id not in self.done_queues:
            logging.warning("get_task: Not sending task %s because its project"
                            "(%s) is not present", task, task.proj_id)
            continue

          if now() < start_time:
            self.todo_queue.put((start_time, task_id))
            logging.debug("get_task: Not sending task. Next task has"
                          " start_time in future")
            # Return the delay until the next job starts.
            return start_time - now() + 1.0

          # From here on we will be submitting the task to the worker.
          # TODO(zfrazier): Add burstable code back in.  See it commented out above.

#          # If it is a "burstable" task, put the next run time as current time.
#          if task.burst > 0:
#            logging.debug("get_task: burst mode enabled.  Setting another copy"
#                          " in queue at time=now, %s", task_id)
#            self.todo_queue.put((now(), task_id))
#            self.tasks[task_id].burst -= 1
#          # If we can't run it immediately, check if we are allowed to run it
#          # again.  If so, place it at now + next_time()
#          else:


          if self.tasks[task_id].tries < task.max_tries:
            logging.debug("get_task: tries < max_tries. putting at time now + "
                          "%s: %s", task.max_time, task_id)
            # regular resubmit.
            self.todo_queue.put((now() + task.max_time, task_id))
          # Otherwise, this is the last run, so add a tracker to the max_time_queue()
          else:
            logging.debug("get_task: tries == max_tries. putting max_timer at time now + "
                          "%s: %s", task.max_time, task_id)
            self.max_time_queue.put((now() + self.tasks[task_id].max_time, task_id))

          self.tasks[task_id].tries += 1
          logging.debug("get_task: sending %s", task)
          return self.tasks[task_id]
      except Queue.Empty:
        logging.debug("get_task: Not sending task. No tasks to be done.")
        continue
      except Exception as error:
        logging.error("Caught an unexpected exception: %s", traceback.format_exc())
        logging.error("Trying to continue")
        continue

  def put_result(self, task_id, error, result):
    """
    Send the results of a computation back to the server.

    This is called by a worker when a task has been completed, or when an
    error occurs during processing.

    :param task_id:    The id of the task being returned
    :param error:    Boolean value, True if an error has occurred.
    :param result:     The result of the computation, or the error message on failure.
    """

    # if error:
    #   check how many other copies are still running/will be run.
    #   if we are the last one, and all returned errors, then return the error
    #   to the caller.
    #   otherwise, resubmit? or should the next run already be in the queue?
    #
    # else:
    #   check if already done with no error.
    #   if so, break
    #   else: 
    #     mark job as complete, and put result in done_queues.

    with self.lock:
      if task_id not in self.tasks:
        logging.warning("put_result: Result not expected. (duplicate or"
                        " finished): %s", task_id)
        return

      task = self.tasks[task_id]

      # Project has been deleted.
      if task.proj_id not in self.done_queues:
        logging.warning("put_result: queue deleted: %s", task.proj_id)
        return

      if error:
        logging.error("put_result: Task threw exception: %s", task)
        if task.tries < task.max_tries:
          self.todo_queue.put((now(), task_id))
          logging.error("put_result: Task failed.  Retry immediately.")
          logging.error("put_result: tries = %s, task.max_tries = %s", task.tries,
                        task.max_tries)
          return
        else:
          logging.error("put_result: Max retries exceeded: %s", task)
          logging.error("put_result: Putting task in done_queue with"
                        " error=True: %s", task.task_id)
          # exhausted all tries
          # put error in done_queues.
          task.error = True
          task.result = result
          # TODO: this only saves most recent error.  Consider adding storage
          # to hold all errors until final return.
          self.done_queues[task.proj_id].put(task)
          del self.tasks[task_id]
      else:
        task.error   = False
        task.result  = result

        self.done_queues[task.proj_id].put(task)
        del self.tasks[task_id]
        logging.debug("put_result: %s", task)


  def get_results(self, proj_id):
    """
    For a given project, return any completed tasks.

    :todo: take a timeout?  call get(timeout) instead of get_nowait()?

    :param proj_id: The project to return tasks for.
    """

    with self.lock:
      if proj_id not in self.done_queues:
        logging.warning("get_results: %s queue deleted", proj_id)
        return []
      results = []
      while True:
        try:
          task = self.done_queues[proj_id].get_nowait()
          results.append(task)
        except Queue.Empty:
          return results


if __name__ == '__main__':

  """Run a server locally."""

  import os
  import sys
  import time
  import threading
  import Queue
  import logging
  import logging.handlers

  from task import Task
  from rpc_server import RPCServer
  from queue_server import QueueServer

  host = "0.0.0.0"
  port = 5011

  server = RPCServer((host, port))
  server.register_instance(QueueServer(server))

  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print "Caught ctrl-c, exiting."
    server.server_close()
