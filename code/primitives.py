# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 


import math

from pygame.locals import *
from pygame import gfxdraw, Rect

# Developers's controls:
DEBUG = False # enables cheats
DEBUG_UPDATES = False
DEBUG_GRID = False


# Arbitrary constants
BUILD_NODE = 1
BUILD_PIPE = 2
DESTROY = 3
UPGRADE = 4
NEUTRAL = 5
OPEN_MENU = 6

SEASON_QUIET = 104
SEASON_STORM = 105
SEASON_ALIEN = 106
SEASON_QUAKE = 107
SEASON_START = 108

MENU_SAVE = 201
MENU_LOAD = 202
MENU_HIDE = 203
MENU_QUIT = 204
MENU_FULLSCREEN = 205
MENU_TUTORIAL = 206
MENU_NEW_GAME = 207
MENU_RES = 208
MENU_MENU = 209
MENU_REVIEW = 210
MENU_BEGINNER = 211
MENU_INTERMEDIATE = 212
MENU_EXPERT = 213
MENU_PREV = 214
MENU_NEXT = 215
MENU_UPDATES = 216
MENU_WEBSITE = 217
MENU_MANUAL = 218
MENU_MUTE = 219
MENU_PEACEFUL = 220

# Mathematical constants
HALF_PI = math.pi * 0.5
TWO_PI = math.pi * 2.0
TWO_THIRDS_PI = ( math.pi * 2.0 ) / 3.0


# Game constants, for tuning:
# steam:
INITIAL_NODE_CAPACITY = 50
INITIAL_NODE_EXCAVATION_DISTANCE = 8
CAPACITY_UPGRADE = 15
RESISTANCE_FACTOR = 0.55 # 0.65
WORK_STEAM_DEMAND = 4.52
STATIC_STEAM_DEMAND = 2.85

# work and health:
HEALTH_UNIT = 10
WORK_UNIT_SIZE = 1
NODE_HEALTH_UNITS = 20
STORM_DAMAGE = 1

# work and upgrades:
NODE_MAX_TECH_LEVEL = 5
NODE_UPGRADE_WORK = 10
CITY_UPGRADE_WORK = 15
PIPE_MAX_TECH_LEVEL = 3
PIPE_UPGRADE_WORK_FACTOR = 1.0
PIPE_UPGRADE_RESISTANCE_FACTOR = 0.8

# timing:
LENGTH_OF_SEASON = 120 # seconds (game days)

# pressure:
PRESSURE_DANGER = 4.0
PRESSURE_WARNING = 6.0
PRESSURE_OK = 8.0
PRESSURE_GOOD = 10.0

# the grid:
GRID_CENTRE = (25,25)
GRID_SIZE = (50,50)

# misc:
CITY_BOX_SIZE = 10
CITY_COLOUR = (192,128,0)
RESOLUTIONS = [
        (800, 600, -4),
        (960, 720, 0),
        (1120, 840, 2),
        (1280, 1024, 4),
        (1440, 1080, 6),
        (1600, 1200, 8),
        (1680, 1050, 8),
]
CGISCRIPT = "http://www.jwhitham.org/cgi-bin/LYU.cgi?"

# things that are set by the difficulty mode:
class Difficulty:
    def __init__(self):
        self.Set(MENU_INTERMEDIATE)
    
    def Set(self, level):
        if ( level in [ MENU_BEGINNER , MENU_TUTORIAL ] ):
            self.DAMAGE_FACTOR = 1.0
            self.CITY_UPGRADE_WORK_PER_LEVEL = 2
            self.GRACE_TIME = 20
            self.CITY_MAX_TECH_LEVEL = 9
            self.BASIC_STEAM_PRODUCTION = 10
            self.STEAM_PRODUCTION_PER_LEVEL = 6
            self.ROCK_QUANTITY = 3000

        elif ( level in [ MENU_INTERMEDIATE, MENU_PEACEFUL ] ):
            self.DAMAGE_FACTOR = 1.4
            self.CITY_UPGRADE_WORK_PER_LEVEL = 3
            self.GRACE_TIME = 10
            self.CITY_MAX_TECH_LEVEL = 12
            self.BASIC_STEAM_PRODUCTION = 6
            self.STEAM_PRODUCTION_PER_LEVEL = 4
            self.ROCK_QUANTITY = 2000

        elif ( level == MENU_EXPERT ):
            self.DAMAGE_FACTOR = 1.7
            self.CITY_UPGRADE_WORK_PER_LEVEL = 4
            self.GRACE_TIME = 5
            self.CITY_MAX_TECH_LEVEL = 15
            self.BASIC_STEAM_PRODUCTION = 4
            self.STEAM_PRODUCTION_PER_LEVEL = 3
            self.ROCK_QUANTITY = 1000

        else:
            print 'Invalid level',level
            assert False


DIFFICULTY = Difficulty()

def Scr_To_Grid((x,y)):
    return (x / __grid_size, y / __grid_size)

def Grid_To_Scr((x,y)):
    return (( x * __grid_size ) + __h_grid_size,
            ( y * __grid_size ) + __h_grid_size )

def Grid_To_Scr_Rect((x,y)):
    (cx,cy) = Grid_To_Scr((x,y))
    return Rect(cx - __h_grid_size_1, cy - __h_grid_size_1, 
            __grid_size_1, __grid_size_1)

def Set_Grid_Size(sz):
    global __grid_size, __grid_size_1, __h_grid_size, __h_grid_size_1
    __grid_size = sz
    __grid_size_1 = sz - 1
    __h_grid_size = sz / 2
    __h_grid_size_1 = __h_grid_size - 1

def Get_Grid_Size():
    return __grid_size

Set_Grid_Size(10)

class Point(object):

    def __init__(self, x, y=None):
        """Point or vector"""
        if isinstance(x, Point):
            self.tup = x.tup

        elif isinstance(x, tuple):
            assert len(x) == 2
            assert y is None, 'y cannot be set when the first param is a tuple'
            self.tup = x

        else:
            assert y is not None, 'y must be set'
            self.tup = (x, y)

    @property
    def x(self):
        return self.tup[0]

    @property
    def y(self):
        return self.tup[1]

    # act as a tuple
    def __len__(self):
        return len(self.tup)

    def __getitem__(self, i):
        return self.tup[i]

    def __add__(self, other):
        if type(self) == type(other):
            return type(self)(self.x + other.x, self.y + other.y)
        if isinstance(other, Rect):
            return self + type(self)(other.topleft)
        raise(TypeError("Incompatible Vector/Point types"))

    def __sub__(self, other):
        return self + (other * -1)

    def __mul__(self, other):
        if type(self) == type(other):
            # vector dot product
            return self.x * other.x + self.y * other.y
        elif type(other) in (int, float):
            # scalar product
            return type(self)(self.x * other, self.y * other)
        raise(TypeError("Incompatible Vector/Point types"))

    def __div__(self, scalar):
        assert isinstance(scalar, int) or isinstance(scalar, float), \
            "Integer or Float required."
        return type(self)(self.x / scalar, self.y / scalar)


    # modulo attribute getter and setter
    @property
    def modulo(self):
        return (self.x ** 2 + self.y ** 2) ** .5

    @modulo.setter
    def modulo(self, m):
        assert isinstance(m, int) or isinstance(m, float), "Integer or Float required."
        a = self.angle
        x = math.sin(a) * m
        y = math.cos(a) * m
        self.tup = (x, y)

    # angle attribute getter and setter
    @property
    def angle(self):
        if self.modulo == 0:
            return 0

        a = math.acos(self.y / self.modulo)
        if self.x >= 0:
            return a
        return math.pi * 2 - a

    @angle.setter
    def angle(self, a):
        assert isinstance(m, int) or isinstance(m, float), "Integer or Float required."
        m = self.modulo
        x = math.sin(a) * m
        y = math.cos(a) * m
        self.tup = (x, y)

    def angle_against(self, other):
        """Angle between two vectors"""
        assert type(self) == type(other), "Incompatible Vector/Point types"
        m = self.modulo
        om = other.modulo
        assert m > 0 and om > 0, 'One of the vectors has zero length'
        cos_alpha = self * other / (m * om)
        return math.acos(cos_alpha)

    def distance(self, other):
        assert type(self) == type(other), "Incompatible Vector/Point types"
        d = other - self
        return d.modulo

    def normalized(self, other=None):
        v = self
        if other is not None:
            v = other - self
        return v / v.modulo

    def orthogonal(self):
        """Create an orthogonal vector"""
        return type(self)(self.y, -1 * self.x).normalized()

    def round_to_int(self):
        self.tup = (int(self.x), int(self.y))

    @property
    def rounded(self):
        return type(self)(int(self.x), int(self.y))

    def __repr__(self):
        return "Vector {%.3f, %.3f}" % (self.x, self.y)

    def set_polar(self, angle=None, modulo=None):
        if modulo == None:
            modulo = self.modulo
        x = math.sin(angle) * modulo
        y = math.cos(angle) * modulo
        self.tup = (x, y)


class PVector(Point):
    """2D vector, measured in pixels"""
    pass

class GVector(Point):
    """2D vector, measured in game units"""
    @property
    def pvector(self):
        """Equivalent vector measured in pixes"""
        return self.in_pixels

    def __getitem__(self, i):
        """The Point/Vector behaves as a tuple, mostly for interacting with pyga
        Return integers measured in pixels
        """
        return int(self.tup[i] * Get_Grid_Size())

    @property
    def in_pixels(self):
        """Equivalent vector measured in pixes"""
        return PVector(Grid_To_Scr(self.tup))


def distance(a, b):
    """Calculate distance between two points (tuples)"""
    d = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
    return d ** (.5)

def draw_ellipse(surface, p, width, color, line_width, center=True, filled=False):
    """Draw an antialiased isometric ellipse
    params: surface, Point, ellipse width in grid sizes (float), color tuple,
        line width (int)
    The ellipse is centered in p
    :returns: (width, height) of the bounding box
    """
    gs = Get_Grid_Size()
    width_pix = width * gs
    if center:
        # center the ellipse
        c = p + Point(gs/2, gs/2)
    else:
        c = p

    if filled:
        w = width_pix
        height = int(w * .574)
        gfxdraw.filled_ellipse(surface, c.x, c.y, int(w), height, color)

    for x in xrange(line_width):
        w = width_pix + x
        height = int(w * .574)
        gfxdraw.aaellipse(surface, c.x, c.y, int(w), height, color)

    return int(w), height


def draw_border(s, r):
    """Draw borders around a surface, used for debugging

    :param s: Surface
    :param r: Rect
    """
    c = (255, 255, 0, 200)
    right = r.right - 1
    bottom = r.bottom - 1
    pygame.draw.lines(s, c, True, (
        (0, 0),
        (right, 0),
        (right, bottom),
        (0, bottom),
    ))

