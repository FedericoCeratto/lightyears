# Test data files

import os
import pygame

from code import resource

def setup():
    tox_env_dir = os.environ.get('TOXENVDIR', None)
    if tox_env_dir:
        # The test is being run under tox
        resource.DATA_DIR = os.path.join(tox_env_dir, 'data')
    else:
        resource.DATA_DIR = os.path.join('.', 'data')

def teardown():
    delattr(resource, 'DATA_DIR')

def test_image_file():
    p = resource.Path('tower_01.png')
    assert os.path.exists(p), "image %s not found" % p

def test_sound_file():
    p = resource.Path('error.ogg', audio=True)
    assert os.path.exists(p), "sound %s not found" % p

