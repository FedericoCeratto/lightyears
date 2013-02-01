#
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
#

# Animated sprites

from pygame.transform import smoothscale, rotate
from random import randint
from time import time
import logging
import pygame

from primitives import Get_Grid_Size, GVector, PVector
from resource import Path as data_path

log = logging.getLogger(__name__)

def memoize(fn):
    """Memoization decorator.
    Keyword arguments are not supported.
    """
    _cache = {}

    def memoizer(*args):
        try:
            return _cache[args]
        except KeyError:
            #log.debug("calling", repr(fn), repr(args))
            _cache[args] = fn(*args)
            return _cache[args]

    return memoizer


@memoize
def load_image(filename):
    """Load an image."""
    return pygame.image.load(data_path(filename))

@memoize
def load_animation(filename):
    """Load an animation."""
    frames = []
    ratio = None
    scale = 1.0
    sequence = 'linear'

    with open(data_path(filename)) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('# Scale:'):
                scale = float(line[8:])
                continue

            if line.startswith('# Sequence: health'):
                sequence = 'health'
                continue

            if line.startswith('# Sequence: random'):
                sequence = 'random'
                continue

            if line.startswith('#'):
                continue # Ignore comments

            img_fname, interval = line.split()
            interval = float(interval) / 1000
            img = load_image(img_fname)
            img = img.convert_alpha()
            frames.append((img, interval))
            if ratio is None: # Calculate ratio on first image
                ratio = img.get_height() / float(img.get_width())

    assert frames, "%s did not load any frame" % filename
    assert sequence in ('linear', 'random', 'health'), \
        "Animation sequence must be linear, health or random"

    log.debug("Loaded anim %s" % filename)
    return scale, sequence, ratio, frames


class StaticSprite(object):
    """A sprite that does not support dynamic rotation/scaling"""
    def __init__(self, filename, pwidth=None, gwidth=None, prerotate=0):
        """Load image from disk"""
        assert filename.endswith('.png')
        self.gcenter = GVector(0, 0)
        img = load_image(filename)
        if prerotate:
            img = rotate(img, prerotate)

        if gwidth:
            pwidth = int(gwidth * Get_Grid_Size())

        if pwidth:
            aw, ah = img.get_size()
            if pwidth != aw:
                pheight = int(float(ah) / aw * pwidth)
                img = smoothscale(img, (pwidth, pheight))

        self._img = img
        self._phalfsize = PVector(self._img.get_size()) / 2

    @property
    def phalfsize(self):
        return self._phalfsize

    def draw(self, output, pcenter=None, pos=None, grayed_out=False, highlighted=False):
        """Draw sprite on a surface"""
        if pcenter:
            pos = pcenter - self.phalfsize
        else:
            assert pos, "pcenter or pos must be specified on draw()"

        if grayed_out:
            i = self.grayed_out()
        elif highlighted:
            i = self.highlight()
        else:
            i = self._img

        output.blit(i, (pos.x, pos.y, 0, 0))

    def set_gcenter(self, x, y):
        """Set sprite center in game units."""
        self.gcenter = GVector(x, y)

    @memoize
    def grayed_out(self):
        """Generate a grayscale image"""
        w, h = self._img.get_size()
        new = pygame.Surface((w, h), pygame.SRCALPHA)

        for x in xrange(w):
            for y in xrange(h):
                red, green, blue, alpha = self._img.get_at((x, y))
                v = 0.3 * red + 0.59 * green + 0.11 * blue
                new.set_at((x, y), (v, v, v, alpha))

        return new

    @memoize
    def highlight(self):
        """Generate a hightlighted image"""
        w, h = self._img.get_size()
        new = pygame.Surface((w, h), pygame.SRCALPHA)

        for x in xrange(w):
            for y in xrange(h):
                red, green, blue, alpha = self._img.get_at((x, y))
                red = min(254, red + 30)
                green = min(254, green + 30)
                blue = min(254, blue + 30)
                new.set_at((x, y), (red, green, blue, alpha))

        return new


class Sprite(object):
    def __init__(self, filename, scale=1.0):
        """Load image from disk"""
        assert filename.endswith('.png')
        self.gcenter = GVector(0, 0)
        self._rotation = 0
        self._zoom = 1
        self.scale(scale)
        i = load_image(filename)
        self._ratio = i.get_height() / float(i.get_width())
        self._rawimg = i
        self._img = None

    def rotate(self, angle):
        """Add rotation"""
        self._rotation += angle

    def zoom(self, v):
        """Add zoom"""
        self._zoom = (self._zoom + v) / 2

    def scale(self, w, h=None):
        """Set scaling in game units. Overrides previous values."""
        self._scaling = (w, h)

    def transform(self):
        """Apply enqueued transformations"""
        self._rotation = round(self._rotation, 3)
        self._zoom = round(self._zoom, 3)
        self._ratio = round(self._ratio, 3)

        self._img = self._transform(self._rawimg, self._rotation, self._scaling,
            self._zoom, self._ratio)
        self._zoom = 1.0
        self._rotation = 0.0

    @staticmethod
    @memoize
    def _transform(img, rotation, scaling, zoom, ratio):

        if scaling:
            w, h = scaling
        else:
            w = img.get_width()

        if zoom != 1:
            w *= zoom

        if h is None:
            h = ratio * w

        w *= Get_Grid_Size()
        h *= Get_Grid_Size()
        new = smoothscale(img, map(int, (w, h)))

        if rotation:
            center = new.get_rect().center
            new = rotate(new, rotation)
            new.get_rect().center = center

        return new

    def update_current_img(self):
        """Update current image"""
        self.transform()

    def draw(self, output, *args):
        """Draw current frame on a surface"""
        self.update_current_img()

        if len(args):
            pcenter = GVector(args[0]).pvector
        else:
            pcenter = self.gcenter.pvector

        phalfsize = PVector(self._img.get_size()) / 2
        pos = pcenter - phalfsize

        output.blit(self._img, (pos.x, pos.y, 0, 0))

    Draw = draw

    def set_gcenter(self, x, y):
        """Set sprite center in game units."""
        self.gcenter = GVector(x, y)

    def reset_animation(self):
        """Used by animations. Performs no actions on static sprites."""
        pass

class AnimatedSprite(Sprite):
    def __init__(self, filename, building=None):
        """Load images from disk"""
        # .anim file format:
        # # Scale: <scale>
        # <filename> <interval (ms)>
        # <filename> <interval (ms)>
        # ...

        assert filename.endswith('.anim')
        self._filename = filename
        self._frames = []
        self._current_frame_num = 0
        self._rotation = 0
        self._zoom = 1
        self.sequence = 'linear' # linear, health or random
        self.building = building

        scale, self.sequence, self._ratio, self._frames = load_animation(filename)
        self.scale(scale)

        self._rawimg, sleeptime = self._frames[self._current_frame_num]
        self._frame_expiry_time = time() + sleeptime


    def update_current_img(self):
        """Update current image"""

        # Switch frame if needed
        if time() > self._frame_expiry_time:

            if self.sequence == 'random':
                # Pick the next frame randomly
                self._current_frame_num = randint(0, len(self._frames) - 1)

            elif self.sequence == 'health' and self.building:
                # Pick a frame number based on the building health
                # (fallback to linear if the health is not set)
                h = self.building.health / float(self.building.max_health)
                h = min(h, 0.999) # h >= 1 would pick a frame that does not exists
                self._current_frame_num = int(len(self._frames) * h)

            else:
                # Increase and restart from 0
                self._current_frame_num += 1
                self._current_frame_num %= len(self._frames)

            self._rawimg, sleeptime = self._frames[self._current_frame_num]
            self._frame_expiry_time = time() + sleeptime

        self.transform()


    def reset_animation(self):
        """Start the animation from the first frame"""
        self._current_frame_num = 0
        self._rawimg, sleeptime = self._frames[self._current_frame_num]
        self._frame_expiry_time = time() + sleeptime
