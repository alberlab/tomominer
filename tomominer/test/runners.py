from tomominer.parallel import rpc_client
import time
import uuid

from tomominer.parallel.task import Task


def test_0(host, port, N=100, seed=0, mean=10, exc_rate=0.0, fail_rate=0.0, max_time=15, max_tries=3, burst=1):

  # generate N jobs.
  # each job is a sleep for a random amount of time determined by mean/var.
  # 

  import random

  random.seed(seed)

  tasks = []
  inv_mean = 1.0/mean
  proj_id = str(uuid.uuid4())

  for i in range(N):
    s = random.expovariate(inv_mean)
    t = Task(proj_id, 'test.sleep', args=(s, exc_rate, fail_rate), max_tries=max_tries, max_time=max_time, burst=burst)
    tasks.append(t)
    print t

  queue = rpc_client.RPCClient(host, port)

  queue.new_project(proj_id)

  results = []
  try:
    queue.put_tasks(tasks)

    all_tasks = set(t.task_id for t in tasks)

    while len(all_tasks):
      res = queue.get_results(proj_id)
      print time.time()
      for r in res:
        print "\t Project: %s Task: %s Args: %s Error: %s Result: %s" % (r.proj_id, r.task_id, r.args, r.error, r.result)
        all_tasks.remove(r.task_id)
        results.append(r)
      time.sleep(1.0)
  finally:
    queue.del_project(proj_id)

  print "host:", host
  print "port:", port
  print "N:", N
  print "seed:", seed
  print "mean:", mean
  print "exc_rate:", exc_rate
  print "fail_rate:", fail_rate
  print "max_time:", max_time
  print "max_tries:", max_tries
  print "burst:", burst

  succ = sum([1 for r in results if not r.error])
  fail = len(results) - succ

  print "succ:", succ
  print "fail:", fail
