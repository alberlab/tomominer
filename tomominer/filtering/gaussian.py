import numpy as np
from numpy.fft import fftn, ifftn, fftshift, ifftshift

def gauss_function(size, sigma):

  grid = gv.grid_displacement_to_center(size)
  dist_sq = gv.grid_distance_sq_to_center(grid) 

  g = (1 / ( (2 * np.pi)**(3/2)  * (sigma**3)) ) * np.exp( - (dist_sq)  / (2 * (sigma**2)))         # gauss function

  return g

# 3D gaussian filtering of a volume (v)
def gaussian_smoothing(v, sigma):
 
  g = gauss_function(size=v.shape, sigma=sigma)


  g_fft = fftn(ifftshift(g));   # use ifftshift(g) to move center of gaussian to origin

  v_conv = np.real( ifftn( fftn(v) * np.conj( g_fft ) ) )

  return v_conv


if __name__ == '__main__':

  import sys

  sigma = float(sys.argv[1])
  f_i = sys.argv[2]
  f_o = sys.argv[3]

  import os
  assert(not os.path.exists(f_o))  # just a little protection of overwriting existing file

  import input_output.file_io as iof
  v_i = iof.get_mrc(f_i)
  v_o = smooth(v_i, sigma)
  v_o = np.array(v_o, order='F')
  
  iof.put_mrc(v_o, f_o)

