#
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
#

# Animated sprites

from random import randint
from time import time

from primitives import Get_Grid_Size, GVector, PVector
from pygame.transform import smoothscale, rotate
from resource import Path as path
import pygame

class StaticSprite(object):
    """A sprite that does not support dynamic rotation/scaling"""
    def __init__(self, filename, pwidth=None):
        """Load image from disk"""
        assert filename.endswith('.png')
        self.gcenter = GVector(0, 0)
        img = pygame.image.load(path(filename))

        if pwidth:
            aw, ah = img.get_size()
            pheight = int(float(ah) / aw * pwidth)
            img = smoothscale(img, (pwidth, pheight))

        self._img = img
        self._phalfsize = PVector(self._img.get_size()) / 2
        self._grayscale_img = None

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

    def grayed_out(self):
        """Generate a grayscale image"""
        if self._grayscale_img:
            return self._grayscale_img

        w, h = self._img.get_size()
        new = pygame.Surface((w, h), pygame.SRCALPHA)

        for x in xrange(w):
            for y in xrange(h):
                red, green, blue, alpha = self._img.get_at((x, y))
                v = 0.3 * red + 0.59 * green + 0.11 * blue
                new.set_at((x, y), (v, v, v, alpha))

        self._grayscale_img = new
        return new

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
        i = pygame.image.load(path(filename))
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
        #if self._img and self._zoom == 1 and self._rotation == 0:
        #    return # No change needed

        img = self._rawimg

        if self._scaling:
            w, h = self._scaling
        else:
            w = img.get_width()

        if self._zoom != 1:
            w *= self._zoom
            self._zoom = 1

        if h is None:
            h = self._ratio * w

        w *= Get_Grid_Size()
        h *= Get_Grid_Size()
        img = smoothscale(img, map(int, (w, h)))

        if self._rotation:
            center = img.get_rect().center
            img = rotate(img, self._rotation)
            img.get_rect().center = center
            self._rotation = 0

        self._img = img

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
        self._frames = []
        self._current_frame_num = 0
        self._rotation = 0
        self._zoom = 1
        self.scale(1.0)
        self.sequence = 'linear' # linear, health or random
        self.building = building

        with open(path(filename)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('# Scale:'):
                    self.scale(float(line[8:]))
                    continue

                if line.startswith('# Sequence: health'):
                    self.sequence = 'health'
                    continue

                if line.startswith('# Sequence: random'):
                    self.sequence = 'random'
                    continue

                if line.startswith('#'):
                    continue # Ignore comments

                img_fname, interval = line.split()
                interval = float(interval) / 1000
                img = pygame.image.load(path(img_fname))
                img = img.convert_alpha()
                self._frames.append((img, interval))

        f.close()
        assert self._frames, "%s did not load any frame" % filename
        assert self.sequence in ('linear', 'random', 'health'), \
            "Animation sequence must be linear, health or random"
        self._ratio = img.get_height() / float(img.get_width())

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
