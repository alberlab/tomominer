
#from tomominer.parallel import Reduce
import os
import tempfile
import logging

import numpy as np
from numpy.fft import fftn, fftshift, ifftshift, ifftn

from tomominer import core
from tomominer.common import cache, lru_memoize, LRUCache

GB = 1024 * 1024 * 1024
mrc_cache = LRUCache(max_size=1*GB, size_fn = lambda x: x.nbytes)

# Use the cache to shorten load times of the request function which parses the
# objects from disk.
@lru_memoize(mrc_cache)
def get_mrc(path):
  """
  Load a subtomogram or mask in MRC format from the filesystem.  The
  mrc_cache decorator, is used to cache previously loaded results.  If
  the subtomogram has been loaded before and still exists in the cache,
  we will use that version instead.  This hopefully will reduce disk load
  times as the most frequently used subtomograms will only be loaded
  once.  We use a cache size of 1 GB.

  :param path: The disk path to load the subtomogram from
  """
  return core.read_mrc(path)

def put_mrc(mrc, path):
  """
  Write a subtomogram to disk.

  :param mrc: The subtomogram or mask as a numpy fortran ordered array.
  :param path: The file to write the volume to.
  """
  # Do not overwrite existing files.
  if not os.path.isfile(path):
    core.write_mrc(mrc, path)

