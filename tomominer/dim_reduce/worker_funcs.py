
import tempfile
import os

import numpy as np
from numpy.fft import fftn, ifftn, fftshift, ifftshift

from tomominer import core
from tomominer import filtering

def neighbor_product(v):
  """

  Calculate product of one voxel and all its neighbors

  :param v:
  """

  # For every possible shift by +/- 1 in any direction, calculate the dot product between then two volumes.  We will store the total values in the 
  siz = list(v.shape)
  siz.append(26)

  P = np.zeros(siz, dtype=np.float32)

  i = 0
  for sx in [-1, 0, 1]:
    for sy in [-1, 0, 1]:
      for sz in [-1, 0, 1]:
        if (sx,sy,sz) == (0,0,0):
          continue
        v2 = v.copy()
        v2 = np.roll(v2, sx, axis=0)
        v2 = np.roll(v2, sy, axis=1)
        v2 = np.roll(v2, sz, axis=2)

        P[:,:,:,i] = v * v2;
        i = i+1
  return P


def pca_stack_diff(avg_vol_key, avg_mask_key, vmal, smoothing_gauss_sigma, voxel_mask_inds, pass_dir):
  """
  Calculate masked differences between subtomograms and gloval average, and
  form a matrix stacking all differences

  :param data:
  :param avg_key:
  :param pass_dir:
  """

  vol_avg  = core.read_mrc(avg_vol_key)
  mask_avg = core.read_mrc(avg_mask_key)

  rows = []

  for vol_key, mask_key, ang, loc in vmal:
    vol  = core.read_mrc(vol_key)
    mask = core.read_mrc(mask_key)

    vol_diff, mask_rot = masked_difference_given_vol_avg_fft(vol, mask, ang, loc, vol_avg, mask_avg, smoothing_gauss_sigma)

    vol_diff = vol_diff.flatten()
    if voxel_mask_inds is not None:
       vol_diff =  vol_diff[voxel_mask_inds]

    rows.append(vol_diff)

  mat = np.vstack(rows)

  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_pcadiff_', suffix='.npy', dir=pass_dir)
  os.close(m_fh)

  np.save(m_name, mat)
  return m_name

def pca_stack_diff_merge(rows, pass_dir):

  rows = [np.load(_) for _ in rows]

  mat = np.vstack(rows)

  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_pcadiff_', suffix='.npy', dir=pass_dir)
  os.close(m_fh)

  np.save(m_name, mat)
  return m_name

def masked_difference_given_vol_avg_fft(v, m, ang, loc, vol_avg_fft, vol_mask_avg, smoothing_gauss_sigma=0):
  """

  :param v:
  :param m:
  :param ang:
  :param loc:
  :param vol_avg_fft:
  :param vol_mask_avg:
  :param smoothing_gauss_sigma:
  """
  v_r = core.rotate_vol_pad_mean(v,ang,loc)
  m_r = core.rotate_mask(m, ang)

  v_r_fft = fftshift(fftn(v_r))
  v_r_msk_dif = np.real(ifftn(ifftshift( (v_r_fft - vol_avg_fft) * m_r * vol_mask_avg )))

  if smoothing_gauss_sigma > 0:
    # mxu:
    # when the subtomograms are very noisy, PCA alone may not work well.
    # Because PCA only process vectors but does consider spetial
    # structures. In such case we can make use spatial information as an
    # additional layer of constrain (or approsimation model) by apply
    # certain amount of gaussian smoothing
    v_r_msk_dif = filtering.gaussian_smoothing(v=v_r_msk_dif, sigma=smoothing_gauss_sigma)

  return (v_r_msk_dif, m_r)


def neighbor_covariance_collect_info(vol_avg_key, mask_avg_key, vmal, pass_dir, smoothing_gauss_sigma=0):
  """
  Collecting information for calculating the neighbor covariance, calculated
  at worker side

  :param avg_key:
  :param vmal:
  :param smoothing_gauss_sigma:
  :param tmp_dir:
  """

  vol_avg  = core.read_mrc(vol_avg_key)
  mask_avg = core.read_mrc(mask_avg_key)

  sum_local = np.zeros(vol_avg.shape)

  neighbor_prods = []

  for vk, mk, ang, loc in vmal:
    v = core.read_mrc(vk)
    m = core.read_mrc(mk)

    v_r_msk_dif, m_r = masked_difference_given_vol_avg_fft(v, m, ang, loc, vol_avg, mask_avg, smoothing_gauss_sigma)


    sum_local += v_r_msk_dif

    neighbor_prods.append(neighbor_product(v_r_msk_dif))

    del v
    del m
    del v_r_msk_dif
    del m_r

  neighbor_prod_sum = sum(neighbor_prods)

  #return sum_local, neighbor_prod_sum

  (_fh1, sum_local_name)  = tempfile.mkstemp(prefix='tm_tmp_sumloc_', suffix='.npy', dir=pass_dir)
  (_fh2, nbr_prod_name)   = tempfile.mkstemp(prefix='tm_tmp_nbrprd_', suffix='.npy', dir=pass_dir)
  os.close(_fh1)
  os.close(_fh2)

  np.save(sum_local_name, sum_local)
  np.save(nbr_prod_name,  neighbor_prod_sum)

  return sum_local_name, nbr_prod_name

def neighbor_covariance_merge(partials, N, pass_dir):
  """
  The final reduce step for collecting sum_local and neighborhood_prod_sum

  """

  avg_global      = sum( np.load(r[0]) for r in partials ) / N
  neighbor_prod_avg   = sum( np.load(r[1]) for r in partials ) / N

  global_neighbor_prod = neighbor_product(avg_global)

  cov = neighbor_prod_avg - global_neighbor_prod

  cov_avg = np.mean(cov, axis=3)
  (_fh, cov_avg_name)   = tempfile.mkstemp(prefix='tm_tmp_covavg_', suffix='.npy', dir=pass_dir)
  np.save(cov_avg_name, cov_avg)
  return cov_avg_name
