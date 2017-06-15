
import numpy as np

from tomominer.common import get_mrc
from tomominer import core

def align(v1, m1, v2, m2, L):
  """
  Align two subtomograms using combined_search function from core.

  :param v1: First volume
  :param m1: First mask
  :param v2: Second volume
  :param m2: Second mask
  :param L:  Angular resolution to search over, 2*pi/L will be the angles searched

  :returns: tuple containing (score, location, angle).  The alignment returned
  is the transformation necessary to align the second volume/mask with the
  first.
  """

  v1 = get_mrc(v1)
  m1 = get_mrc(m1)
  v2 = get_mrc(v2)
  m2 = get_mrc(m2)

  try:
    res = core.combined_search(v1, m1, v2, m2, L)
  except:
    res = []
  if res:
    return res[0]
  else:
    # align will return None if there is no alignment found.  We instead
    # return a very poor match.
    return (0.0, np.zeros((3,)), np.zeros((3,)))


def real_space_rotation_align(v1, m1, v2, m2, L=36):
  """
  Fast real space rotation alignment according to Xu ISMB2013

  :param v1: First volume
  :param m1: First mask
  :param v2: Second volume
  :param m2: Second mask
  :param L: Angular resolution to search over, 2*pi/L will be angles searched.
  :returns: Tuple with correlation score, and best routation found.

  :note: This only performs a rotational search.  Volumes v1 and v2 must be
  translated such that the center of the volume is the point to be treated as
  the rotaitonal origin.  The search will be performed by rotation about the
  center of the tomogram.
  """

  # Round trip through FFT space to apply masks,
  # warning: fftshift breaks order='F'
  v1f = fftshift(fftn(v1)) * m1
  v2f = fftshift(fftn(v2)) * m2

  v1fi = np.real(ifftn(ifftshift(v1f)))
  v2fi = np.real(ifftn(ifftshift(v2f)))

  m1sq = np.square(m1)
  m2sq = np.square(m2)

  radius = int( max(v1.shape) / 2 )
  radii = list(range(1,radius+1)) # radii must start from 1, not 0!
  radii = np.array(radii, dtype=np.float)

  cor12 = core.rot_search_cor(v1=v1fi, v2=v2fi, radii=radii, L=max_l)

  sqt_cor11 = np.sqrt( core.rot_search_cor( v1=np.square(np.abs(v1f)), v2=m2sq, L=max_l, radii=radii ) )
  sqt_cor22 = np.sqrt( core.rot_search_cor( v1=m1sq, v2=np.square(np.abs(v2f)), L=max_l, radii=radii ) )

  cor_array = cor12 / (sqt_cor11 * sqt_cor22)

  (cors, angs) = core.local_max_angles(cor=cor_array)
  i = np.argsort(-cors)
  cors = cors[i]
  angs = angs[i,:]

  # Return correlation/angle
  return (cors[0], angs[0])

def batch_align(v1_key, m1_key, vm_keys, L):
  """
  Align subtomograms using combined_search function from core.

  :param v1: First volume
  :param m1: First mask
  :param vm_keys: List of (vol_key, mask_key) pairs for second volume.
  :param L:  Angular resolution to search over, 2*pi/L will be the angles searched

  :returns: list of tuples containing (score, location, angle).  The alignment returned
  is the transformation necessary to align the second volume/mask with the
  first.
  """

  v1 = get_mrc(v1_key)
  m1 = get_mrc(m1_key)

  results = []

  for v2_key,m2_key in vm_keys:

    v2 = get_mrc(v2_key)
    m2 = get_mrc(m2_key)

    try:
      res = core.combined_search(v1, m1, v2, m2, L)
    except:
      res = []
    if res:
      results.append(res[0])
    else:
      # align will return None if there is no alignment found.  We instead
      # return a very poor match.
      results.append((0.0, np.zeros((3,)), np.zeros((3,))))
  return results

def align_to_templates(v1_key, m1_key, template_dict, L):
  """
  Align a subtomogram against a dictionary of templates.  Return the key of
  the best match, and the transformation of the best alignment.

  :param v1: A volume to align
  :param m1: A mask to align
  :param template_dict: A dictionary mapping from keys, to (vol,mask) pairs.
  :param L: Angular resolution.  2*pi/L is the angular discretization.

  :returns: tuple containing the the key of the best aligning template, and
  the best result. The result is the output of the combined search. (score,
  loc, ang)
  """

  best_score    = 0
  best_template   = None
  best_match    = None

  for tkey in template_dict:
    v2_key,m2_key = template_dict[tkey]

    res = align(v2_key, m2_key, v1_key, m1_key, L)

    if res[0] > best_score:
      best_score    = res[0]
      best_template   = tkey
      best_match    = res

  return best_template, best_match
