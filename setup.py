#!/usr/bin/env python

from setuptools import setup
from glob import glob
import os
import sys

from code.startup import __version__

CLASSIFIERS = map(str.strip,
"""
License :: OSI Approved :: GNU General Public License v2 (GPLv2)
Natural Language :: English
Operating System :: POSIX :: Linux
Programming Language :: Python
""".splitlines())

data_files_globs = [
    ['audio', ['*.ogg']],
    ['data', ['*.png', '*.anim']],
]

print("-- [data files] --")
data_files = []
for dirname, globs in data_files_globs:
    expanded_fnames = set()
    for g in globs:
        ffn = os.path.join(dirname, g)
        expanded_fnames.update(glob(ffn))

    data_files.append((dirname, sorted(expanded_fnames)))
    print(dirname)
    for fn in sorted(expanded_fnames):
        print("  %s" % fn)

print("------")

#build_py3 = sys.version_info >= (3,)

setup(
    name="lightyears",
    version=__version__,
    license="GPLv2",
    classifiers=CLASSIFIERS,
    install_requires=[
        #'zeromq',
        'pygame',
        'libsdl1.2debian',
        'libsdl1.2-dev',
        'nose',
    ],
    packages=['code'],
    platforms=['Linux'],
    test_suite='nose.collector',
    tests_require=[
       'nose'
    ],
    data_files=data_files,
    #use_2to3=build_py3
)
