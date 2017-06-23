
import os
import numpy as np

from tomominer.parallel import Runner

def volume_average(host, port, data, vol_shape, pass_dir, use_fft):
  """
  Calculate the average volume of a given list of volumes.

  :param host:  Host running server to submit work units to.
  :param port:  Port of server to submit work units to.
  :param data:
  :param vol_shape: Dimensions of a subtomogram (3 element list/vector)
  :param pass_dir:  Temporary directory to stash results in.
  :param use_fft: If true, do the average in FFT space.

  :returns: The key to lookup the average volume.

  """

  runner = Runner(host, port)

  if use_fft:
    map_fn  = "average.vol_avg_fft_map"
    reduce_fn = "average.vol_avg_fft_reduce"
  else:
    map_fn  = "average.vol_avg_map"
    reduce_fn = "average.vol_avg_reduce"

  # TODO: use heuristic or data from Runner() to determine

  N = len(data)

  if N < 1000:
    chunk_size = 50
  else:
    chunk_size = 100
  chunk_size = max(N/256, 50)

  max_time = max((chunk_size / 100 + 1) * 120, 600)

  # break data up into chunks and make reduce tasks.
  tasks = []

  for i in range(0, N, chunk_size):
    t = runner.make_task(map_fn, args=(data[i:i+chunk_size], vol_shape, pass_dir), max_time=max_time)
    tasks.append(t)

  #print "split into %d tasks" % (len(tasks),)

  # Overwrite data! Now the results from the first round!

  data = []
  # run all first round reduce tasks.
  for res in runner.run_batch(tasks):
    data.append(res.result)


  t = runner.make_task(reduce_fn, args=(data, vol_shape, N, pass_dir))

  res = runner.run_single(t)

  # clean up all the temporary files.
  for temp_vol, temp_mask in data:
    os.remove(temp_vol)
    os.remove(temp_mask)
  return res.result
