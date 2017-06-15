import logging
import os
import sys
import time
import traceback

from Queue import Empty
from multiprocessing import Process, Queue

from rpc_client import RPCClient
from task import Task


# This now forks, and runs the requested program in a separate process.
# The problem is that we lose most of the benifits of cacheing.  We need to
# decide if this is worth trying to hack around.  We can pass in a
# multiprocessing.Queue, and use that as an interface to the original
# processes cache.  But is that not general enough?

class QueueWorker:

  def __init__(self, host, port, instance=None, get_task_timeout=30, get_task_sleep=10, poll_freq=10):
    """
    A worker that connects to a Queue Server and processes jobs.

    :param host: The IP host to connect to.
    :param port: The port to contact the server on.
    :param instance: An object with a set of functions that we will be running on behalf of connecting clients.
    """

    self.work_queue = RPCClient(host,port)
    self.instance   = instance

  def run(self):
    """
    Enter a loop connecting to the server to get work, and return results.
    """

    while True:
      task = self.work_queue.get_task(timeout=30)

      if isinstance(task, (int, float)):
        time.sleep(min(task, 30))
      else:
        task = self._dispatch(task)
        self.work_queue.put_result(task.task_id, task.error, task.result)


  def _dispatch(self, task):
    """
    Try to run the requested method (task.method), and return the result (task.result)

    Note this needs to recurse down to find the function.

    :param task: The task to run locally.
    """


    if task.method.startswith('_'):
      task.fail("method starts with underscore")

    fun_path = task.method.split(".")
    instance = self.instance

    for i in range(len(fun_path)):
      p = fun_path[i]
      if not hasattr(instance, p):
        logging.error("valid methods of %s are: %s", ".".join(fun_path[:i]), dir(instance))
        task.fail("method not found")
        return task
      else:
        instance = getattr(instance, p)

    if not callable(instance):
      task.fail("method not callable")
      return task

    try:
      # This queue will be used to communicate the result from the child process.
      Q = Queue()

      # A local wrapper around the task function.
      def proc_run(q, f, args, kwargs):
        try:
          res = f(*args, **kwargs)
          q.put(res)
        except Exception as e:
          q.put(e)

      proc = Process(target=proc_run, args=(Q, instance, task.args, task.kwargs))
      proc.start()
      start_time = time.time()

      while True:
        try:
          res = Q.get(timeout=10)
          proc.join()

          if isinstance(res, Exception):
            logging.error("task failed with exception, re-raising")
            raise res
          else:
            logging.info("task success.  returning result.")
            task.result = res
          break
        except Empty:
          if not proc.is_alive():
            # process was killed, and never sent the raised
            # exception.  We will raise our own here.
            raise RuntimeError("Worker process crashed")

          # Check to see if the result is still needed by the
          # server, or if another worker has finished it.
          state = self.work_queue.get_state(task.proj_id, task.task_id)

          if not state:
            proc.terminate()
            task.fail("Killing task because server no longer tracking.")
            break
          # if task has exceeded max_time, kill it.
          if time.time() - start_time > task.max_time:
            proc.terminate()
            task.fail("Killing task for exceeding max_time: %s (used: %s)" % (task.max_time, time.time() - start_time))
            break
    except Exception as ex:
      logging.error(str(ex))
      traceback.print_exc()
      task.fail(str(ex))

    return task


if __name__ == '__main__':

  class Dummy(QueueWorker):
    def __init__(self, host, port):
      QueueWorker.__init__(self, host, port)

    def echo(self, msg):
      return msg

    def reverser(self, msg):
      return msg[::-1]

    def adder(self, x, y=3):
      return x + y

  worker = Dummy("127.0.0.1", 5011)

  worker.run()
