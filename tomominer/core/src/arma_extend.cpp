#include <cstdlib> // div/ldiv

#include "arma_extend.hpp"

arma::uvec arma::ind2sub(const arma::uvec &shape, int idx)
{
  size_t d = shape.n_elem;

  arma::uvec sub(d);
  arma::uvec m(d);

  m(d-1) = 1;
  for(size_t i = 1; i < d; i++)
    m(d-i-1) = m(d-i)*shape(i-1);
  
  for(size_t i = 0; i < d; i++)
  {
    ldiv_t res = ldiv(idx, m(i));
    sub(d-i-1) = res.quot;
    idx    = res.rem;
  }

  return sub;
}
