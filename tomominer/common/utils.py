from scipy import stats
import numpy as np
from numpy.fft import fftshift, fftn
from numpy import sum, abs, sqrt

def snr(v1, v2):
  """
  Estimate the signal to noise ratio given two realizations of a noisy data set.

  """

  pr = stats.pearsonr(v1.flatten(), v2.flatten())
  corr = pr[0]

  return corr / (1.0 - corr)

def fourier_shell_correlation(v1, v2, bandwidth_radius = 1.0):


  size = v1.shape

  assert( v1.shape == v2.shape )

  x = np.mgrid[0:size[0], 0:size[1], 0:size[2]]
  for i in range(3):
    x[i] -= size[i]//2

  R = np.sqrt(np.square(x).sum(axis=0))

  v1f = fftshift(fftn(v1))
  v2f = fftshift(fftn(v2))

  fsc = np.zeros(np.min(size)//2)

  for i in range(0,np.min(size)//2):
    mask = (abs(R-(i+1)) < 0.5)
    c1 = v1f[mask]
    c2 = v2f[mask]

    fsc[i] = np.real(sum(c1 * np.conj(c2))) / np.sqrt( sum(abs(c1)**2) * sum(abs(c2)**2))

  return fsc
