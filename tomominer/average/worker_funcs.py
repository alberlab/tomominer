import os
import time
import tempfile

from tomominer import core
from tomominer.common import get_mrc, put_mrc

import numpy as np
from numpy.fft import fftn, fftshift, ifftshift, ifftn


def vol_avg_fft_map(data, vol_shape, pass_dir):
  """
  Local work for computing average of all volumes.  This calculates a sum
  over the given subset of volumes.  Several of these are done and
  combined with vol_avg_global.  This is the map() stage of the global
  averaging step.

  :param vol_shape: The dimensions of the subtomograms we will be processing
  :param vmal_in: The data for incoming data.  A list of (volume, mask, angle, disp) tuples.
  :param v_out_key: The file location to write our local averaged volume to.
  :param m_out_key: The file location to write our local averaged mask to.
  """

  # temporary collection of local volume, and mask.
  vol_sum  = np.zeros(vol_shape, dtype=np.complex128, order='F')
  mask_sum = np.zeros(vol_shape, dtype=np.float64,  order='F')

  # iterate over all volumes/masks and incorporate data into averages.
  # volume_key, mask_key, angle offset, location offset.
  for vk, mk, ang, loc in data:

    # load vol/mask.
    vol  = get_mrc(vk)
    mask = get_mrc(mk)


    # rotate vol and mask according to angle/loc.
    vol  = core.rotate_vol_pad_mean(vol, ang, loc)
    mask = core.rotate_mask(mask, ang)

    vol_sum  += (fftshift(fftn(vol)) * mask)
    mask_sum += mask

  # volume/mask temporary accumulation locations.
  (v_fh, v_name) = tempfile.mkstemp(prefix='tm_tmp_vafmv_', suffix='.npy', dir=pass_dir)
  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_vafmm_', suffix='.npy', dir=pass_dir)
  os.close(v_fh)
  os.close(m_fh)

  np.save(v_name, vol_sum)
  np.save(m_name, mask_sum)

  return v_name, m_name


def vol_avg_fft_reduce(vm_in, vol_shape, n_vol, pass_dir):
  """
  Collect the output from the local vol_avg_fft_map tep.  Complete the sum, and
  write a final volume and mask average.

  :param vm_in:    The list of volume and maks pairs that are the subtotals
            computed so far.
  :param vol_shape:  3 element vector describing the shape of the volumes and
            masks.
  :param n_vol:    The total number of volumes that contributed to the
            subtotals we have, (necessary for the average calculation)
  :pass_dir:       Where to write the output.

  :returns: A tuple containing the volume and mask file names.  The data is
  computed and then written to disk in the pass_dir.

  """

  mask_threshold = 1.0

  fft_sum  = np.zeros(vol_shape, dtype=np.complex128, order='F')
  mask_sum = np.zeros(vol_shape, dtype=np.float64,  order='F')

  for vk,mk in vm_in:
    vol = np.load(vk)
    fft_sum += vol

    mask = np.load(mk)
    mask_sum += mask

  # This avoids RuntimeWarning: invalid value encountered in divide.
  flag_t = (mask_sum >= mask_threshold)
  tem_fft = np.zeros(vol_shape, dtype=np.complex128, order='F')
  tem_fft[flag_t] = fft_sum[flag_t] / mask_sum[flag_t]
  #tem_fft[mask_sum < mask_threshold] = 0

  vol_avg = np.asfortranarray(np.real(ifftn(ifftshift(tem_fft))))
  mask_avg = mask_sum / n_vol

  (v_fh, v_name) = tempfile.mkstemp(prefix='tm_tmp_vafrv_', suffix='.mrc', dir=pass_dir)
  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_vafrm_', suffix='.mrc', dir=pass_dir)
  os.close(v_fh)
  os.close(m_fh)
  core.write_mrc(vol_avg, v_name)
  core.write_mrc(mask_avg, m_name)

  return v_name, m_name


def vol_avg_map(data, vol_shape, pass_dir):
  """
  Local work for computing average of all volumes.  This calculates a sum
  over the given subset of volumes.  Several of these are done and
  combined with vol_avg_global.  This is the map() stage of the global
  averaging step.

  :param vol_shape: The dimensions of the subtomograms we will be processing
  :param vmal_in: The data for incoming data.  A list of (volume, mask, angle, disp) tuples.
  :param v_out_key: The file location to write our local averaged volume to.
  :param m_out_key: The file location to write our local averaged mask to.
  """

  # temporary collection of local volume, and mask.
  vol_sum  = np.zeros(vol_shape, dtype=np.float64, order='F')
  mask_sum = np.zeros(vol_shape, dtype=np.float64, order='F')

  # iterate over all volumes/masks and incorporate data into averages.
  # volume_key, mask_key, angle offset, location offset.
  for vk, mk, ang, loc in data:

    # load vol/mask.
    vol  = get_mrc(vk)
    mask = get_mrc(mk)

    # rotate vol and mask according to angle/loc.
    vol  = core.rotate_vol_pad_mean(vol, ang, loc)
    mask = core.rotate_mask(mask, ang)

    vol_sum  += vol
    mask_sum += mask

  # volume/mask temporary accumulation locations.
  (v_fh, v_name) = tempfile.mkstemp(prefix='tm_tmp_vamv_', suffix='.npy', dir=pass_dir)
  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_vamm_', suffix='.npy', dir=pass_dir)
  os.close(v_fh)
  os.close(m_fh)

  np.save(v_name, vol_sum)
  np.save(m_name, mask_sum)

  return v_name, m_name


def vol_avg_reduce(vm_in, vol_shape, n_vol, pass_dir):
  """
  Collect the output from the local vol_avg_map step.  Complete the sum, and
  write a final volume and mask average.

  :param vm_in:    The list of volume and maks pairs that are the subtotals
            computed so far.
  :param vol_shape:  3 element vector describing the shape of the volumes and
            masks.
  :param n_vol:    The total number of volumes that contributed to the
            subtotals we have, (necessary for the average calculation)
  :pass_dir:       Where to write the output.

  :returns: A tuple containing the volume and mask file names.  The data is
  computed and then written to disk in the pass_dir.

  :todo: should this use mask_threshold?
  """

  mask_threshold = 1.0

  vol_sum  = np.zeros(vol_shape, dtype=np.float64, order='F')
  mask_sum = np.zeros(vol_shape, dtype=np.float64, order='F')

  for vk,mk in vm_in:
    vol = np.load(vk)
    vol_sum += vol

    mask = np.load(mk)
    mask_sum += mask

  vol_avg  = vol_sum / n_vol
  mask_avg = mask_sum / n_vol

  (v_fh, v_name) = tempfile.mkstemp(prefix='tm_tmp_varv_', suffix='.mrc', dir=pass_dir)
  (m_fh, m_name) = tempfile.mkstemp(prefix='tm_tmp_varm_', suffix='.mrc', dir=pass_dir)
  os.close(v_fh)
  os.close(m_fh)
  core.write_mrc(vol_avg, v_name)
  core.write_mrc(mask_avg, m_name)

  return v_name, m_name
