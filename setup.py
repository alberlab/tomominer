from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from numpy import get_include

cpp_core = Extension('tomominer.core.core',
                    sources = [ 'tomominer/core/src/affine_transform.cpp',
                                'tomominer/core/src/align.cpp',
                                'tomominer/core/src/arma_extend.cpp',
                                'tomominer/core/src/dilate.cpp',
                                'tomominer/core/src/fft.cpp',
                                'tomominer/core/src/geometry.cpp',
                                'tomominer/core/src/interpolation.cpp',
                                'tomominer/core/src/io.cpp',
                                'tomominer/core/src/legendre.cpp',
                                'tomominer/core/src/rotate.cpp',
                                'tomominer/core/src/sht.cpp',
                                'tomominer/core/src/wigner.cpp',
                                'tomominer/core/cython/wrap_core.cpp',
                                'tomominer/core/cython/core.pyx',
                              ],
                    libraries           = ['m', 'fftw3', 'armadillo', 'blas', 'lapack', ],
                    library_dirs        = ["/usr/usc/gnu/mpc/1.0.1/lib/", "/auto/cmb-04/fa/zfrazier/local/lib64/", ],
                    include_dirs        = [get_include(), '/usr/include', "tomominer/core/src/",],
                    #include_dirs        = [get_include(), '/usr/include', "tomominer/core/src/", "/usr/usc/gnu/mpc/1.0.1/include/", "/auto/rcf-47/zfrazier/local/include/"],
                    extra_compile_args  = ['-std=c++11'],
                    language='c++',
)

setup(  name        = 'tomominer',
        version     = '1.0.0',
        author      = 'Alber Lab (USC)',
        description = 'Subtomogram Analysis and Mining Software',
        license     = 'GPLv3',  # TODO: figure this out. Required by FFTW?
        url         = '',
        platforms   = ['x86_64'],
        ext_modules = [cpp_core],
        packages    = ['tomominer',
                       'tomominer.align',
                       'tomominer.average',
                       'tomominer.classify',
                       'tomominer.cluster',
                       'tomominer.common',
                       'tomominer.core',
                       'tomominer.dim_reduce',
                       'tomominer.filtering',
                       'tomominer.parallel',
                       'tomominer.test',
                      ],
        package_dir = { 'tomominer'         : 'tomominer',
                        'tomominer.core'    : 'tomominer/core/cython/',
                      },
        scripts     = ['bin/tm_worker', 'bin/tm_server', 'bin/tm_classify', 'bin/tm_average', 'bin/tm_check', 'bin/tm_watch', 'bin/tm_corr', 'bin/tm_fsc', 'bin/tm_test', 'bin/tm_run_workers_local', 'bin/tm_smooth'],
        cmdclass   = {'build_ext': build_ext},
     )
