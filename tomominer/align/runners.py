
import numpy as np

from tomominer.parallel import Runner

# TODO: Add real-space rotational alignment runner.
# See worker function code: real_space_rotation_align()

def all_vs_all_alignment(host, port, data1, data2, L):
  """
  Given two sets of (v,m) pairs, compute the optimal alignment between all
  members of each group.

  :param host:  Host running server to submit work units to.
  :param port:  Port of server to submit work units to.
  :param data1:   First set of (vol,mask) pairs.
  :param data2:   Second set of (vol,mask) pairs.
  :param L:     Discretization of angles to use.  Spacing is 2\pi/L

  :returns:     List of lists.  result[i][j] is the alignment score between
          data1[i] and data2[j], and the transformation necessary to
          align data2[j] to data1[i].
  """

  runner = Runner(host, port)

  tasks = []
  tracker = {}
  results = [ [None for _1 in data2] for _2 in data1 ]

  for i, d1 in enumerate(data1):
    for j, d2 in enumerate(data2):
      t = runner.make_task('align.align', args=(d1[0], d1[1], d2[0], d2[1], L))
      tasks.append(t)
      tracker[t.task_id] = (i,j)

  for res in runner.run_batch(tasks):
    i,j = tracker[res.task_id]
    results[i][j] = res.result
  return results


def one_vs_all_alignment(host, port, target, data, L):
  """
  Compute the optimal alignment of all (v,m) pairs in data to the (v,m) pair
  known as target.

  :param host:   Host running server to submit work units to.
  :param port:   Port of server to submit work units to.
  :param target:   A (volume, mask) tuple to compare all elements of data to.
  :param data:   Set of (volume, mask) we will use to compute all distances.
  :param L:    Discretization of angles to use.  Spacing is 2\pi/L

  :returns: Dictionary mapping from arguments to the result.
  """

  runner = Runner(host, port)
  tasks = []
  tracker = {}

  N = len(data)

  # TODO: tuning.
  chunk_size = max(5, N / 1000)

  for idx, i in enumerate(range(0,N,chunk_size)):
    chunk = data[i:i+chunk_size]
    t = runner.make_task('align.batch_align', args=(target[0], target[1], chunk, L), burst=1)

    tracker[t.task_id] = idx
    tasks.append(t)

  results = [None for _ in tasks]
  for res in runner.run_batch(tasks):
    results[tracker[res.task_id]] = res.result

  results = [r for b in results for r in b]
  return results


def pairwise_alignment(host, port, data, L):
  """
  Calculate alignment scores for all vs. all for elements in data.

  :param host: host of server to submit jobs to
  :param port: port of server to submit jobs to
  :param data: (volume, mask) list for all subtomograms
  :param L:  parameter for alignment

  :returns:  Only the score of alginments between all elements of data vs
  all other elements.  The result is a numpy matrix of scores.
  """

  runner = Runner(host, port)

  # TODO: consider breaking into chunks.  For now do each one seperate.

  tasks = []

  corr    = np.eye(len(data), dtype=np.float)
  transform = [[None for y in data] for x in data]

  pos_map = {}

  for i,d1 in enumerate(data):
    for j,d2 in enumerate(data):
      if d2 <= d1:
        continue
      t = runner.make_task('align.align', args=(d1[0], d1[1], d2[0], d2[1], L))
      pos_map[t.task_id] = (i,j)
      tasks.append(t)

  for res in runner.run_batch(tasks):
    # The (i,j) result is the transform applied to data[j] to align with data[i]
    i,j = pos_map[res.task_id]
    score, loc, ang = res.result
    transform[i][j] = ( loc,  ang)
    transform[j][i] = (-loc, -ang)
    corr[i,j] = score
    corr[j,i] = score
  return corr, transform


def align_vols_to_templates(host, port, data, templates, L):
  """
  Run align() between a each data element and all templates. Return the best hit to a template for each data element.

  :param host:     Host to submit work units to.
  :param port:     Port of server we submit work units to
  :param data:     A list of (volume, mask) pairs of tomograms we are going to align to a set of templates.
  :param templates:  The set of templates we are going to align each subtomogram to.
  :param L:      Angle discretization.  sampling angle is 2\pi/L

  :returns:      List of (args,results) from alignment results.
  """

  # TODO: Come up with a better return structure.

  runner = Runner(host, port)

  tasks = []

  # TODO: break into chunks.
  for d1 in data:
    t = runner.make_task('align.align_to_templates', args=(d1[0], d1[1], templates, L))
    tasks.append(t)
  results = []

  for res in runner.run_batch(tasks):
    results.append((res.args, res.result))
  return results


#def merge_templates(host, port, data1, data2, L):
#  """
#  Calculate all alignment between members of data_1 and members of data_2
#
#  :param host   server to submit work units to.
#  :param port   port of server to submit work units to.
#  :param data1  A list of templates. (volume, mask) pairs.
#  :param data2  A second list of templates (volume, mask) pairs
#  :param L    Angle discritization to use in alignment, sample angle = 2\pi/L
#
#  :return The alignments found between the two template groups.
#  """
#
#  # TODO: is this function needed?  Is it identical to something else above?
#  # This is currently never called.
#
#  runner = Runner(host, port)
#
#  # TODO: consider breaking into chunks.  For now do each one seperate.
#
#  tasks = []
#
#  # TODO: check order of parameters to combined_search if we use this code.
#  for d1 in data1:
#    for d2 in data2:
#      t = runner.make_task('core.combined_search', args=(d1[0], d1[1], d2[0], d2[1], L))
#      tasks.append(t)
#
#  results = []
#  # run all first round reduce tasks.
#  for res in runner.run_batch(tasks):
#    results.append((res.args, res.result))
#  return results
