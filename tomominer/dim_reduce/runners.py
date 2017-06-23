from collections import defaultdict
import os.path

import pickle
import sys

import time
import random
import math
import copy
import logging

import numpy as np
from numpy.fft import fftn, ifftn, fftshift, ifftshift

from math import sqrt

from tomominer.common import get_mrc, put_mrc
from tomominer.parallel import Runner
from tomominer import core

from funcs import dimension_reduction_randomized_pca_train
from empca import empca
from worker_funcs import neighbor_product


def pca_stack_diff(host, port, vmal, global_avg_vm, pass_dir, smoothing_gauss_sigma=0, voxel_mask_inds=None):
  """
  :todo: documentation

  :param host: Host where a tm_server instance is running
  :param port: Port where a tm_server instance is running
  :param global_avg_vm: Disk location of average volume, and mask
  :param smoothing_gauss_sigma: ???
  :param voxel_mask_inds Indices: to be used in the dimension reduction.
  """

  runner = Runner(host, port)

  # TODO: better method.
  #chunk_size = max(len(vmal)/50, 20)
  chunk_size = int(sqrt(len(vmal)))

  avg_vol_key, avg_mask_key = global_avg_vm

  tasks = []

  task_order = {}
  for i,idx in enumerate(range(0, len(vmal), chunk_size)):
    t = runner.make_task('dim_reduce.pca_stack_diff', args=(avg_vol_key, avg_mask_key, vmal[idx:idx+chunk_size], smoothing_gauss_sigma, voxel_mask_inds, pass_dir))
    tasks.append(t)
    task_order[t.task_id] = i

  rows = [None for _ in range(len(tasks))]

  for res in runner.run_batch(tasks):
    rows[task_order[res.task_id]] = res.result

  t = runner.make_task('dim_reduce.pca_stack_diff_merge', allow_resubmit=False, args=(rows, pass_dir))
  res = runner.run_single(t)

  for r in rows:
    os.remove(r)

  #return res
  # actually return the loaded data.
  return np.load(res.result)

  # TODO: In Min's version the matrices are returned directly to the root
  # node, where they are combined instead of being merged on a computational node.
  #return np.vstack(rows)


def neighbor_covariance_avg_parallel(host, port, vmal, global_avg_vm, pass_dir, smoothing_gauss_sigma=0):
  """
  TODO: documentation

  calculate the covariance between neighbor voxels, then take average

  :param host:
  :param port:
  :param avg_key:
  :param data:
  :param smoothing_gauss_sigma:
  """

  start_time = time.time()
  runner = Runner(host, port)

  tasks = []
  # TODO: better method.
  #chunk_size = len(vmal)/50
  chunk_size = int(sqrt(len(vmal)))
  #chunk_size = max(chunk_size, 20)
  #chunk_size = min(chunk_size, 100)
  avg_vol_key, avg_mask_key = global_avg_vm

  for i in range(0, len(vmal), chunk_size):
    t = runner.make_task('dim_reduce.neighbor_covariance_collect_info', args=(avg_vol_key, avg_mask_key, vmal[i:i+chunk_size], pass_dir))
    tasks.append(t)


  results = [ _.result for _ in runner.run_batch(tasks) ]

  # TODO: consider moving this to a finalizer function.

  t = runner.make_task('dim_reduce.neighbor_covariance_merge', allow_resubmit=False, args=(results, len(vmal), pass_dir))
  res = runner.run_single(t)
  cov_avg_name = res.result

  for sum_loc, nbr_prod in results:
    os.remove(sum_loc)
    os.remove(nbr_prod)


  cov_avg = np.load(cov_avg_name)
  return cov_avg
#
#  avg_global      = sum( np.load(r[0]) for r in results ) / len(vmal)
#  neighbor_prod_avg   = sum( np.load(r[1]) for r in results ) / len(vmal)
#
#  global_neighbor_prod = neighbor_product(avg_global)
#
#  cov = neighbor_prod_avg - global_neighbor_prod
#
#  cov_avg = np.mean(cov, axis=3)
#
#  print "Calculated neighbor covariance : %2.6f sec" % (time.time() - start_time)
#
#  return cov_avg


# Code dumped from filtering/gaussian.py and general_util/vol.py


def covariance_filtered_pca(host, port, vmal, dims, global_avg_vm, cov_avg_file, pass_dir, gauss_smoothing_sigma=0, max_features=1000, n_iter=15):
  """
  Calculate average covariance between neighbor voxels, then gaussian smooth
  and segment to identify a small amount of voxels as features for PCA
  analysis

  :TODO: documentation

  :param host:
  :param port:
  :param vmal:
  :param dims:
  :param global_avg_vm:
  :param cov_avg_file:
  :param pass_dir:
  :param gauss_smoothing_sigma:
  :param max_features:
  :param n_iter:
  """

  # Other parameters:
  #
  # * cov_avg_min_cutoff_ratio=0.0
  # * pca_op=None
  # * out_dir=None
  #
  # Add back in as needed.
  #
  # TODO: there are 3 different gauss_smoothing variables?  Are they actually all necessary?


  start_time = time.time()

  # TODO: wrap the load in a try, if it fails also do else case.

  # try to load existing covariance data.
  if os.path.exists(cov_avg_file):
    with open(cov_avg_file) as f:
      cov_avg = np.load(f)
  else:
    # If the covariance data does not exists, calculate it, and save the data.
    cov_avg = neighbor_covariance_avg_parallel(host, port, vmal, global_avg_vm, pass_dir, gauss_smoothing_sigma)

    with open(cov_avg_file, 'wb') as f:
      np.save(f, cov_avg)

  if gauss_smoothing_sigma > 0:
    cov_avg = utils.smooth(cov_avg, sigma=gauss_smoothing_sigma)

  # restrict number of features to max_features
  #
  # if there are more features then max_feature_num, update value.
  max_features = min(max_features, cov_avg.size)

  #print "Running Covariance Filtered PCA with max_features =", max_features
  #print

  # sort all values and save indices.  unroll into a single array.
  sorted_inds = np.argsort(cov_avg, axis=None)

  # identify the cutoff to use, by finding the max_feature_num value in the array.
  cutoff = cov_avg.flatten()[sorted_inds[-max_features-1]]

  # extract indices of cov_avg greater then cutoff.
  voxel_mask_inds = np.flatnonzero(cov_avg > cutoff)

  # perform PCA using only the voxels determined by voxel_mask_inds
  mat = pca_stack_diff(host, port, vmal, global_avg_vm, pass_dir, gauss_smoothing_sigma, voxel_mask_inds)

  # For now skip the masking stage.
#  # Mask out missing values
#  empca_weight = ~np.isnan(mat)
#  mat[~empca_weight] = 0.0

  empca_weight = np.ones(mat.shape)

  # weight every feature according to its corresponding average correlation
  cov_avg = cov_avg.flatten()
  for i, ind_t in enumerate(voxel_mask_inds):
    empca_weight[:,i] *= cov_avg[ind_t]

  # note: need to watch out the R2 values to see how much variation can be
  # explained by the estimated model, if the value is small, need to increase
  # dims
  pca = empca(data=mat, weights=empca_weight, nvec=dims, niter=n_iter)

  red = pca.coeff

  #print "PCA with covariange thresholding  : %2.6f sec" % (time.time() - start_time)

  return red
