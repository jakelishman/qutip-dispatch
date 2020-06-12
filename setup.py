#!/usr/bin/env python

import setuptools
from Cython.Build import cythonize
import numpy as np
import glob

kwargs = {
    'include_dirs': [np.get_include()],
    'extra_compile_args': ['-O3', '-funroll-loops'],
    'extra_link_args': [],
    'language': 'c++',
    'define_macros': [("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
}
extensions = [
    setuptools.Extension('data.'+name[5:-4], sources=[name], **kwargs)
    for name in glob.glob('data/*.pyx')
]
directives = {'profile': False}

ext_modules = cythonize(extensions,
                        annotate=True,
                        compiler_directives=directives)

setuptools.setup(ext_modules=ext_modules)
