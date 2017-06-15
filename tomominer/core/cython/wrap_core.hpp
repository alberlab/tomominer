#ifndef TOMO_CYTHON_HPP
#define TOMO_CYTHON_HPP

#include <string>

void wrap_write_mrc(double *vol, unsigned int n_r, unsigned int n_c, unsigned int n_s, std::string filename);
void *wrap_read_mrc(std::string filename, double **vol, unsigned int *n_r, unsigned int *n_c, unsigned int *n_s);

void *wrap_combined_search(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v1_data, double *m1_data, double *v2_data, double *m2_data, unsigned int L, unsigned int *n_res, double **res_data);

void *wrap_rot_search_cor(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v1_data, double *v2_data, unsigned int n_radii, double *radii_data, unsigned int L, unsigned int *n_cor_r, unsigned int *n_cor_c, unsigned int *n_cor_s, double **cor);
void *wrap_local_max_angles(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *cor_data, unsigned int peak_spacing, unsigned int *n_res, double **res_data);

void wrap_rotate_vol_pad_mean(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v_data, double *rm_data, double *dx_data, double *res_data);
void wrap_rotate_vol_pad_zero(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v_data, double *rm_data, double *dx_data, double *res_data);
void wrap_rotate_mask(unsigned int n_r, unsigned int n_c, unsigned int n_s, double *v_data, double *rm_data, double *res_data);
void wrap_del_cube(void *c);
void wrap_del_mat(void *v);
#endif // guard
