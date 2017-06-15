
#include <string>
#include <iostream>

#include "align.hpp"
#include "io.hpp"

void wrap_write_mrc(double *vol, unsigned int n_r, unsigned int n_c, unsigned int n_s, std::string filename)
{
  arma::cube V(vol, n_r, n_c, n_s, false, true);
  write_mrc(V, filename.c_str());
}

void *wrap_read_mrc(std::string filename, double **vol, unsigned int *n_r, unsigned int *n_c, unsigned int *n_s)
{

  // can we create the cube and tell it not to own its own data, so we can
  // use its own cleanup as a stack variable without using new, but keep the
  // double * array around?  Or do we have to pass in an array for that to
  // happen?

  arma::cube *v = new arma::cube(read_mrc(filename.c_str()));

  *vol = v->memptr();
  *n_r = v->n_rows;
  *n_c = v->n_cols;
  *n_s = v->n_slices;
  return (void *)v;
}

void *wrap_combined_search(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v1_data, double *m1_data, double *v2_data, double *m2_data, unsigned int L, unsigned int *n_res, double **res_data)
{
  arma::cube v1(v1_data, n_r, n_c, n_s, false, true);
  arma::cube m1(m1_data, n_r, n_c, n_s, false, true);
  arma::cube v2(v2_data, n_r, n_c, n_s, false, true);
  arma::cube m2(m2_data, n_r, n_c, n_s, false, true);

  std::vector<std::tuple<double, arma::vec3, euler_angle> > res = combined_search(v1, m1, v2, m2, L);
  //std::vector<boost::tuple<double, arma::vec3, euler_angle> > res = combined_search(v1, m1, v2, m2, L);

  arma::mat *ret = new arma::mat(res.size(), 7);

  *res_data = ret->memptr();
  *n_res  = res.size();

  for(size_t i = 0; i < res.size(); i++)
  {
    (*ret)(i,0) = std::get<0>(res[i]);
    (*ret)(i,1) = std::get<1>(res[i])(0);
    (*ret)(i,2) = std::get<1>(res[i])(1);
    (*ret)(i,3) = std::get<1>(res[i])(2);
    (*ret)(i,4) = std::get<2>(res[i])(0);
    (*ret)(i,5) = std::get<2>(res[i])(1);
    (*ret)(i,6) = std::get<2>(res[i])(2);
  }
  return (void *)ret;
}

void *wrap_rot_search_cor(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v1_data, double *v2_data, unsigned int n_radii, double *radii_data, unsigned int L, unsigned int *n_cor_r, unsigned int *n_cor_c, unsigned int *n_cor_s, double **cor)
{
  arma::cube v1(v1_data, n_r, n_c, n_s, false, true);
  arma::cube v2(v2_data, n_r, n_c, n_s, false, true);

  // Create wigner D-matrices, used later.
  //! @note consider precomputation and loading from disk, or saving across combined_search runs.
  std::vector<arma::mat> wig_d = wigner_d(M_PI/2.0, L);

  arma::vec3 mid_co = get_fftshift_center(v1);
  
  // one shell for every cube. N/2 shells.
  std::vector<double> radius(n_radii);
  for(size_t i = 0; i < n_radii; i++)
    radius[i] = radii_data[i];

  arma::cx_cube cor_cx = rot_search_cor(v1, v2, L, radius, wig_d, mid_co);
  // WARNING: currently we only return the real part of the rotation
  // correlation array
  arma::cube *cor_p = new arma::cube( arma::real(cor_cx)  );

  *cor = cor_p->memptr();

  *n_cor_r = cor_p->n_rows;
  *n_cor_c = cor_p->n_cols;
  *n_cor_s = cor_p->n_slices;

  return (void *)cor_p;
}

void *wrap_local_max_angles(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *cor_data, unsigned int peak_spacing, unsigned int *n_res, double **res_data)
{
  arma::cube cor(cor_data, n_r, n_c, n_s, false, true);

  // find local maximum in cors matrix. 
  // each element of cors corresponds to a different rotation angle.
  std::vector<euler_angle> angs;
  std::vector<double> scores;

  std::tie(angs, scores) = local_max_angles(cor, peak_spacing);

  std::vector<std::tuple<double, arma::vec3, euler_angle> > angs_locs_scores;

  // remove redundant angles. 
  std::tie(angs, scores) = angle_list_redundancy_removal_zyz(angs, scores, 0.01);

  // convert result into a matrix
  arma::mat *ret = new arma::mat(angs.size(), 4);

  *res_data = ret->memptr();
  *n_res  = angs.size();

  for(size_t i = 0; i < angs.size(); i++)
  {
    (*ret)(i,0) = scores[i];
    (*ret)(i,1) = angs[i][0];
    (*ret)(i,2) = angs[i][1];
    (*ret)(i,3) = angs[i][2];
  }
  return (void *)ret;

}

void wrap_rotate_vol_pad_mean(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v_data, double *ea_data, double *dx_data, double *res_data)
{
  arma::cube   v(v_data, n_r, n_c, n_s,   false, true);
  arma::vec3  ea = arma::vec3(ea_data);
  arma::vec3  dx = arma::vec3(dx_data);
  
  arma::mat33 rm = rot_matrix(ea);

  arma::cube rot = rotate_vol_pad_mean(v, rm, dx);

  for(size_t i = 0; i < rot.n_elem; i++)
    res_data[i] = rot(i);
  return;
}


void wrap_rotate_vol_pad_zero(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v_data, double *ea_data, double *dx_data, double *res_data)
{
  arma::cube   v(v_data, n_r, n_c, n_s,   false, true);
  arma::vec3  ea(ea_data);
  arma::vec3  dx(dx_data);
  arma::mat33 rm = rot_matrix(ea);

  arma::cube rot = rotate_vol_pad_zero(v, rm, dx);

  for(size_t i = 0; i < rot.n_elem; i++)
    res_data[i] = rot(i);
  return;
}


void wrap_rotate_mask(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *m_data, double *ea_data, double *res_data)
{
  arma::cube   m(m_data, n_r, n_c, n_s,   false, true);
  arma::vec3  ea(ea_data);
  arma::mat33 rm = rot_matrix(ea);

  arma::cube rot = rotate_mask(m, rm);

  for(size_t i = 0; i < rot.n_elem; i++)
    res_data[i] = rot(i);
  return;
}


void wrap_del_cube(void *v)
{
  arma::cube *c = (arma::cube *)v;
  delete c;
}
void wrap_del_mat(void *v)
{
  arma::mat *m = (arma::mat *)v;
  delete m;
}
