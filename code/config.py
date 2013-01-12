# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

import startup, os, extra, primitives
try:
    import json
except ImportError:
    import simplejson as json

from logging import getLogger
log = getLogger(__name__)

CFG_VERSION = "1.5"

cfg = None

class Config(object):
    def __init__(self, delete_file=False):
        """Read/initialize config"""
        self.version = CFG_VERSION
        (w, h, fs) = primitives.RESOLUTIONS[ 0 ]
        self.resolution = (w, h)
        self.fullscreen = False
        self.mute = True
        self.font_scale = fs
        self.seen_before = False
        self.keys = {
            'n': 'build node',
            's': 'build super node',
            'p': 'build pipe',
            'd': 'destroy item',
            'u': 'upgrade item',
            'q': 'quit to menu',
        }


        home = extra.Get_Home()
        if home is None:
            self._filename = "config.dat"
        else:
            self._filename = os.path.join(home, ".lightyears.cfg")

        if delete_file:
            # Don't load old configuration
            self.save()
            return

        try:
            with open(self._filename) as f:
                d = json.load(f)

            # Ignore unsupported versions
            assert d['version'] == CFG_VERSION, "Unsupported config version"

            for k, v in d.iteritems():
                self.__dict__[k] = v

        except Exception, e:
            log.error("Unable to read config file: %s" % e)
            self.save()


    def save(self):
        """Save config to disk."""
        # Save instance's public attributes
        d = dict((k,v) for k,v in self.__dict__.items() if not k.startswith('_'))
        try:
            with open(self._filename, 'w') as f:
                json.dump(d, f, sort_keys=True, indent=2)
        except Exception, e:
            log.error("Unable to write config file: %s" % e)


