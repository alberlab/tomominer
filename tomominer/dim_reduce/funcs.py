
#from tomominer.parallel import Reduce
import numpy as np
import os
import tempfile
from tomominer import core
from tomominer.common import get_mrc, put_mrc

from numpy.fft import fftn, fftshift, ifftshift, ifftn

import logging

# parallel transform all subtomograms (indexed by inds according order of
# data) given trained pca

def dimension_reduction_randomized_pca_transform(pca, avg_vol, data, inds):
  """
  :todo: documentation
  """

  mat = dimension_reduction_randomized_pca_stack_dif(avg_vol, data)
  red = pca.fit_transform(mat)

  return {'inds':inds, 'red':red}

def dimension_reduction_randomized_pca_stack_diff(avg_vol_key, data):
  """
  :TODO: documentation
  :TODO: rename
  :TODO: move somewhere else
  """
  vol_avg = get_mrc(avg_vol_key)
  vol_avg_fft = fftshift(fftn(vol_avg))

  mat = np.zeros((len(data), vol_avg.size))

  for i, (vk, mk, ang, loc) in enumerate(data):
    # load vol/mask.
    vol  = get_mrc(vk)
    mask = get_mrc(mk)

    # rotate vol and mask according to angle/loc.
    vol_r  = core.rotate_vol_pad_mean(vol, ang, loc)
    mask_r = core.rotate_mask(mask, ang)

    v_dif = np.real(ifftn(ifftshift(fftshift(fftn(vol_r) - vol_avg_fft) * mask_r)))

    mat[i, :] = v_dif.flatten()

  return mat


def dimension_reduction_randomized_pca_train(dims, avg_vol_key, data, transform=False):
  """
  :todo: documentation
  """

  mat = dimension_reduction_randomized_pca_stack_diff(avg_vol_key, data)

  from sklearn.decomposition import RandomizedPCA
  pca = RandomizedPCA(n_components=dims)
  pca.fit(mat)

  if not transform:
    return pca

  red = pca.fit_transform(mat)
  return pca, red

