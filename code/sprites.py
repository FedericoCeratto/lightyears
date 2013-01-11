#
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
#

# Animated sprites

from time import time
from pygame.transform import smoothscale, rotate
from resource import Path as path
import pygame
from primitives import Get_Grid_Size, GVector, PVector

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


class AnimatedSprite(Sprite):
    def __init__(self, filename):
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

        with open(path(filename)) as f:
            for line in f:
                if line.startswith("# Scale:"):
                    self.scale(float(line[8:]))
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
        self._ratio = img.get_height() / float(img.get_width())
        self._frame_expiry_time = time() + self._frames[0][1]
        self._rawimg = self._img = self._frames[0][0]

    def update_current_img(self):
        """Update current image"""

        # Switch frame if needed
        if time() > self._frame_expiry_time:
            self._frame_expiry_time = time() \
                + self._frames[self._current_frame_num][1]
            self._current_frame_num += 1
            self._current_frame_num %= len(self._frames)

            self._rawimg = self._frames[self._current_frame_num][0]

        self.transform()

