import numpy as np
from numpy.fft import fftn, ifftn, fftshift, ifftshift
from scipy.signal import butter, lfilter

def grid_displacement_to_center(size):
  # construct a gauss function whose center is at center of volume
  grid = np.mgrid[0:size[0], 0:size[1], 0:size[2]]
  mid_co = np.array(size) / 2

  for dim in range(3):
    grid[dim, :, :, :] -= mid_co[dim]

  return grid

def grid_distance_sq_to_center(grid):
  dist_sq = np.zeros(grid.shape[1:])
  for dim in range(3):
    dist_sq += np.squeeze(grid[dim, :, :, :]) ** 2
  return dist_sq

def gauss_function(size, sigma):
  grid = grid_displacement_to_center(size)
  dist_sq = grid_distance_sq_to_center(grid)
  # gauss function
  g = (1.0 / ( (2 * np.pi)**(3.0/2)  * (sigma**3)) ) * np.exp( - (dist_sq)  / (2.0 * (sigma**2)))
  return g

def gaussian_smoothing(v, sigma):
  """Smooth volume v, with spherical gaussian filter.

  Gaussian filter has single parameter sigma, which is symmetric standard
  deviation.

  Returns the volume v, after Gaussian smoothing is applied.
  """

  g = gauss_function(size=v.shape, sigma=sigma)
  # use ifftshift(g) to move center of gaussian to origin
  g_fft = fftn(ifftshift(g))
  v_conv = np.real( ifftn( fftn(v) * np.conj( g_fft ) ) )
  return v_conv

def spheremask(v, radius, sigma):
  """Apply a spherical mask to volume v.

  All values outside of radius are set to zero.  If sigma > 0, this boundary is
  relaxed, and the values near the boundary decay exponetially out to 2*sigma.
  """
  dist_sq = grid_distance_sq_to_center(v)
  mask = np.ones(dist_sq.shape)
  mask[dist_sq > radius*radius] = 0

  if sigma > 0:
    sigma2 = sigma * sigma
    mask[mask == 0] = np.exp(-((np.sqrt(dist_sq) - radius)/sigma)**2)
    Mask[mask < np.exp(-2)] = 0
  return vol * mask

# TODO: generalize to bandpass filtering.
def lowpass_smoothing(v, high, sigma=0):
  """Apply a low pass filter to volume v.

  Apply the filter in Fourier space.  Trim all frequencies higher then :high:.
  Frequencies are measured in pixel units.  If sigma > 0, Gaussian
  smoothing is applied frequencies on the edge.  So instead of a sharp cutoff
  at frequency :high:, there is decay from :high: to :high:+2*sigma.
  """
  dist_sq = grid_distance_sq_to_center(v)
  mask = (dist_sq <= high*high)

  v_fft = fftshift(fftn(v))
  v_fft_filt = v_fft * mask
  v_filt = np.real(ifftn(ifftshift(v_fft_filt)))

  if sigma > 0:
    return np.real(ifftn(ifftshift(spheremask(fftshift(fftn(v_filt)), high, sigma))))
  return v_filt


#def low_bandpass_smoothing(v, cutoff, order=5):
#  b,a = butter(order, Wn=cutoff)
#  # Default filter is lowpass.
#  # Wn is point of 1/sqrt(2) signal loss in passband.  Normalized on 0,1 where
#  # 1 is nyquist freq.
#
#  # Next apply the smoothing.
#  return lfilter(b,a,v)
