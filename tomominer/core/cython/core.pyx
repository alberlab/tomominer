import numpy as np
cimport numpy as np
cimport cython

from libcpp.string cimport string

cdef extern from "wrap_core.hpp":
  cdef void wrap_write_mrc(double *, unsigned int, unsigned int, unsigned int, string) except +
  cdef void *wrap_read_mrc(string, double **, unsigned int *, unsigned int *, unsigned int *) except +
  cdef void *wrap_combined_search(unsigned int, unsigned int, unsigned int, double *, double *, double *, double *, unsigned int, unsigned int *, double **) except +
  cdef void *wrap_rot_search_cor(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v1_data, double *v2_data, unsigned int n_radii, double *radii_data, unsigned int L, unsigned int *n_cor_r, unsigned int *n_cor_c, unsigned int *n_cor_s, double **cor) except +
  cdef void *wrap_local_max_angles(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *cor_data, unsigned int peak_spacing, unsigned int *n_res, double **res_data) except +
  cdef void wrap_rotate_vol_pad_mean(unsigned int, unsigned int, unsigned int, double *, double *, double *, double *) except +
  cdef void wrap_rotate_vol_pad_zero(unsigned int, unsigned int, unsigned int, double *, double *, double *, double *) except +
  cdef void wrap_rotate_mask(unsigned int, unsigned int, unsigned int, double *, double *, double *) except +
  cdef void wrap_del_cube(void *c) except +
  cdef void wrap_del_mat(void *c) except +

@cython.boundscheck(False)
@cython.wraparound(False)
def write_mrc(np.ndarray[np.double_t, ndim=3] vol, str filename):
  """
  TODO: documentation
  """

  cdef double *vol_data
  cdef unsigned int n_r, n_c, n_s

  if not vol.flags.f_contiguous:
    vol = vol.copy(order='F')

  vol_data = <double *>vol.data
  n_r = vol.shape[0]
  n_c = vol.shape[1]
  n_s = vol.shape[2]

  wrap_write_mrc(vol_data, n_r, n_c, n_s, filename)
  return

@cython.boundscheck(False)
@cython.wraparound(False)
def read_mrc(str filename):
  """
  TODO: documentation
  """

  cdef double *v_data
  cdef unsigned int n_r, n_c, n_s
  cdef np.ndarray[np.double_t, ndim=3] vol
  cdef void *cube_ptr

  cube_ptr = wrap_read_mrc(filename, &v_data, &n_r, &n_c, &n_s)

  vol = np.empty( (n_r, n_c, n_s), dtype=np.double, order='F')

  cdef double *np_data = <double*> vol.data

  cdef size_t i
  for i in range(n_r*n_c*n_s):
    np_data[i] = v_data[i]

  wrap_del_cube(cube_ptr)

  return vol


@cython.boundscheck(False)
@cython.wraparound(False)
def combined_search(np.ndarray[np.double_t, ndim=3] vol1, np.ndarray[np.double_t, ndim=3] mask1, np.ndarray[np.double_t, ndim=3] vol2, np.ndarray[np.double_t, ndim=3] mask2, unsigned int L):
  """
  TODO: documentation
  """

  cdef double *v1_data
  cdef double *m1_data
  cdef double *v2_data
  cdef double *m2_data

  cdef double *res_data
  cdef unsigned int n_res

  cdef np.ndarray[np.double_t, ndim=2] res

  cdef void   *mat_ptr

  cdef unsigned int n_r, n_c, n_s

  if not vol1.flags.f_contiguous:
    vol1 = vol1.copy(order='F')
  if not mask1.flags.f_contiguous:
    mask1 = mask1.copy(order='F')
  if not vol2.flags.f_contiguous:
    vol2 = vol2.copy(order='F')
  if not mask2.flags.f_contiguous:
    mask2 = mask2.copy(order='F')

  v1_data = <double *> vol1.data
  m1_data = <double *>mask1.data
  v2_data = <double *> vol2.data
  m2_data = <double *>mask2.data

  n_r = vol1.shape[0]
  n_c = vol1.shape[1]
  n_s = vol1.shape[2]

  mat_ptr = wrap_combined_search(n_r, n_c, n_s, v1_data, m1_data, v2_data, m2_data, L, &n_res, &res_data)


  res = np.empty( (n_res, 7), dtype=np.double, order='F')

  cdef double *np_data = <double*> res.data

  cdef size_t i
  for i in range(n_res*7):
    np_data[i] = res_data[i]

  wrap_del_mat(mat_ptr)

  R = []

  for i in range(n_res):
    R.append((res[i,0], np.array(res[i,1:4]), np.array(res[i,4:])))
  return R


@cython.boundscheck(False)
@cython.wraparound(False)
def rot_search_cor(np.ndarray[np.double_t, ndim=3] v1, np.ndarray[np.double_t, ndim=3] v2, np.ndarray[np.double_t, ndim=1] radii, unsigned int L=36):

  # in these cases, the calcualtion may stuck
  if v1.max() == v1.min():
    raise RuntimeError('v1.max() == v1.min()')
  if v2.max() == v2.min():
    raise RuntimeError('v2.max() == v2.min()')

  if not v1.flags.f_contiguous:
    v1 = v1.copy(order='F')
  if not v2.flags.f_contiguous:
    v2 = v2.copy(order='F')

  cdef double *v1_data
  cdef double *v2_data
  v1_data = <double *> v1.data
  v2_data = <double *> v2.data

  cdef unsigned int n_r, n_c, n_s

  n_r = v1.shape[0]
  n_c = v1.shape[1]
  n_s = v1.shape[2]

  cdef unsigned int n_radii
  n_radii = len(radii)

  if not radii.flags.f_contiguous:
    radii = radii.copy(order='F')
  cdef double *radii_data
  radii_data = <double *> radii.data

  cdef unsigned int n_cor_r, n_cor_c, n_cor_s
  cdef double *cor_data
  cdef void *cor_ptr

  cor_ptr = wrap_rot_search_cor(n_r, n_c, n_s, v1_data, v2_data, n_radii, radii_data, L, &n_cor_r, &n_cor_c, &n_cor_s, &cor_data)

  cdef np.ndarray[np.double_t, ndim=3] cor
  cor = np.empty( (n_cor_r, n_cor_c, n_cor_s), dtype=np.double, order='F')

  cdef double *cor_data_np = <double*> cor.data

  cdef size_t i
  for i in range(n_cor_r * n_cor_c * n_cor_s):
    cor_data_np[i] = cor_data[i]

  wrap_del_cube(cor_ptr)

  return cor


@cython.boundscheck(False)
@cython.wraparound(False)
def local_max_angles(np.ndarray[np.double_t, ndim=3] cor, unsigned int peak_spacing=8):

  if not cor.flags.f_contiguous:
    cor = cor.copy(order='F')

  cdef double *cor_data
  cor_data = <double *> cor.data

  cdef unsigned int n_r, n_c, n_s
  n_r = cor.shape[0]
  n_c = cor.shape[1]
  n_s = cor.shape[2]


  cdef unsigned int n_res
  cdef double *res_data

  res_ptr = wrap_local_max_angles(n_r, n_c, n_s, cor_data, peak_spacing, &n_res, &res_data)

  cdef np.ndarray[np.double_t, ndim=2] res
  res = np.empty( (n_res, 4), dtype=np.double, order='F')

  cdef double *res_data_np = <double*> res.data

  cdef size_t i
  for i in range(n_res*4):
    res_data_np[i] = res_data[i]

  wrap_del_mat(res_ptr)

  cors = res[:,0]
  angs = res[:,1:]

  return (cors, angs)


@cython.boundscheck(False)
@cython.wraparound(False)
def rotate_vol_pad_mean(np.ndarray[np.double_t, ndim=3] vol, np.ndarray[np.double_t, ndim=1] ea, np.ndarray[np.double_t, ndim=1] dx):
  """
  TODO: documentation
  """

  cdef double *vol_data
  cdef double *ea_data
  cdef double *dx_data
  cdef double *res_data

  cdef np.ndarray[np.double_t, ndim=3] res

  cdef unsigned int n_r, n_c, n_s

  if not vol.flags.f_contiguous:
    vol = vol.copy(order='F')

  n_r = vol.shape[0]
  n_c = vol.shape[1]
  n_s = vol.shape[2]

  res = np.empty((n_r, n_c, n_s), dtype=np.double, order='F')

  vol_data = <double *>vol.data
  ea_data  = <double *> ea.data
  dx_data  = <double *> dx.data
  res_data = <double *>res.data

  wrap_rotate_vol_pad_mean(n_r, n_c, n_s, vol_data, ea_data, dx_data, res_data);
  return res



@cython.boundscheck(False)
@cython.wraparound(False)
def rotate_vol_pad_zero(np.ndarray[np.double_t, ndim=3] vol, np.ndarray[np.double_t, ndim=1] ea, np.ndarray[np.double_t, ndim=1] dx):
  """
  TODO: documentation
  """

  cdef double *vol_data
  cdef double *ea_data
  cdef double *dx_data
  cdef double *res_data

  cdef np.ndarray[np.double_t, ndim=3] res

  cdef unsigned int n_r, n_c, n_s

  if not vol.flags.f_contiguous:
    vol = vol.copy(order='F')

  n_r = vol.shape[0]
  n_c = vol.shape[1]
  n_s = vol.shape[2]

  res = np.empty((n_r, n_c, n_s), dtype=np.double, order='F')

  vol_data = <double *>vol.data
  ea_data  = <double *> ea.data
  dx_data  = <double *> dx.data
  res_data = <double *>res.data

  wrap_rotate_vol_pad_zero(n_r, n_c, n_s, vol_data, ea_data, dx_data, res_data);
  return res

@cython.boundscheck(False)
@cython.wraparound(False)
def rotate_mask(np.ndarray[np.double_t, ndim=3] mask, np.ndarray[np.double_t, ndim=1] ea):
  """
  TODO: documentation
  """

  cdef double *mask_data
  cdef double *ea_data
  cdef double *res_data

  cdef np.ndarray[np.double_t, ndim=3] res

  cdef unsigned int n_r, n_c, n_s

  if not mask.flags.f_contiguous:
    mask = mask.copy(order='F')

  n_r = mask.shape[0]
  n_c = mask.shape[1]
  n_s = mask.shape[2]

  res = np.empty((n_r, n_c, n_s), dtype=np.double, order='F')

  mask_data = <double *>mask.data
  ea_data  = <double *> ea.data
  res_data = <double *>res.data

  wrap_rotate_mask(n_r, n_c, n_s, mask_data, ea_data, res_data);
  return res
