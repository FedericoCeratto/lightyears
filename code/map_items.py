# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

# Items that you will find on the map.
# All inherit from the basic Item.

import pygame, math
from pygame import gfxdraw
from pygame.locals import *

import bresenham , intersect , extra , stats , resource , draw_obj , sound
from primitives import *
from random import randint
import random
from steam_model import Steam_Model
import time
from mail import New_Mail
import sprites

import logging
log = logging.getLogger(__name__)

class Item(pygame.sprite.Sprite, object):
    def __init__(self, name):
        self.pos = None
        self.name_type = name
        self.draw_obj = None
        self.emits_steam = False
        self.tutor_special = False

    @property
    def _tlp(self):
        return Point(self.pos) * Get_Grid_Size()

    def Draw(self, output):
        self.draw_obj.Draw(output, self.pos, (0,0))

    def Draw_Mini(self, output, soffset):
        self.draw_obj.Draw(output, self.pos, soffset)

    def Draw_Selected(self, output, highlight):
        return None

    def Draw_Popup(self, output):
        return None

    def Get_Information(self):
        """Generate a colored item name"""
        color = (255, 255, 0) if self.owned_by_me else (80, 80, 80)
        return [(color, 20, self.name_type)]

    def Prepare_To_Die(self):
        pass

    def Take_Damage(self, dmg_level=1):
        # Basic items have no health and therefore can't be damaged
        return False

    def Is_Destroyed(self):
        return False

    def Sound_Effect(self):
        pass

    def draw_ellipse(self, surface, p, width, color, line_width):
        """Draw an antialiased isometric ellipse
        params: surface, Point, ellipse width (float), color tuple,
            line width (int)
        :returns: (width, height) of the bounding box
        """
        return draw_ellipse(surface, p, width, color, line_width, center=False)

    def __repr__(self):
        """Generate instance  __repr__"""
        return "%s(%s)" % (self.__class__.__name__, repr(self.pos))


class Vehicle(Item):
    """Abstract class for ground or air vehicles"""

    def __init__(self, pos=None, network=None, vehicles=None):
        self._net = network
        self.pos = pos
        self.pos = Point(randint(1, 30), randint(1, 30))
        #self.pos = Point(5, 20)
        self.cruise_speed = 2
        self._twopi = math.pi * 2
        self._status = 'lift'
        self._anim_cnt = 0
        self._anim_startstop_cnt = 0
        self._momentum = Point(0, 0)
        self._anim_u_turn = 0
        self._anim_float = 0
        self._force = Point(0, 0)

    def _load_sprites(self, fname):
        """Load movement sprites from a 3x3 mosaic"""
        mosaic = resource.Load_Image(fname)
        sprites = []
        for n in (5, 8, 7, 6, 3, 0, 1, 2, 5):
            s = pygame.Surface((40, 40), flags=pygame.SRCALPHA)
            x = n / 3 * -40
            y = n % 3 * -40
            s.blit(mosaic, (x, y))
            s = pygame.transform.smoothscale(s, (20, 20))
            #s = pygame.transform.smoothscale(s, (10, 10))
            sprites.append(s)

        return sprites

    @property
    def _centerp(self):
        return self._tlp + Point(10, 10)

    @property
    def _simple_angle(self):
        return int(self._momentum.angle / self._twopi * 8 + .5) % 9

    def _drive(self):
        """Drive the vehicle forward"""
        #v = Point(0, 0)
        #angle = self._simple_angle / 8.0 * self._twopi - 0.2
        #v.set_polar(angle=angle, modulo=self._momentum.modulo)

        self.pos += self._momentum / Get_Grid_Size()
        #self.pos = self.pos + v / Get_Grid_Size()

    def _steer(self, angle):
        """Steer"""
        self._momentum.angle += angle
        self._momentum.angle %= self._twopi

    def _u_turn(self):
        """Animate U-turn"""
        self._anim_u_turn += 1
        self.angle += self._twopi / 120
        if hasattr(self, '_float'):
            self._float()
        if self._anim_u_turn > 60:
            self._drive()
            self._anim_u_turn = 0

    def _repulsion(self, source):
        """Calculate repulsion generated by a gravity source"""
        v = self.pos - source
        if v.modulo == 0:
            return v * 0.000000001
        repulsion = 10 / (v.modulo / 3) ** 2
        v.modulo = repulsion
        return v
        return v.normalized() * repulsion

    def _avoid(self):
        force = Point(0.0, 0.0)
        #for r in self._net.rock_list + self._net.node_list:
        for r in self._net.rock_list:
            force += self._repulsion(Point(r.pos))

        if hasattr(self, '_vehicles'):
            for v in self._vehicles:
                if v != self:
                    force += self._repulsion(v.pos)

        q = Point(self.pos.x, 1.0)
        force += self._repulsion(q)

        q = Point(1.0, self.pos.y)
        force += self._repulsion(q)

        q = Point(self.pos.x, 45.0)
        force += self._repulsion(q)

        q = Point(45.0, self.pos.y)
        force += self._repulsion(q)

        self._force = force

        self._force_c = (0,0,0, 100)

        if force.modulo > 3:
            # negative product between momentum and force: the vehicle
            # is facing an obstacle
            if self._force * self._momentum < 0:

                # slow down
                if self._momentum.modulo > self.cruise_speed / 8:
                    self._momentum.modulo *= 0.95
                #self.draw_ellipse(
                #    self._surf,
                #    self._centerp.rounded,
                #    Get_Grid_Size() * .2,
                #    self._force_c,
                #    1)

                # product against a vector orthogonal to the momentum
                if self._force * self._momentum.orthogonal() > 0:
                    # right side
                    self._force_c = (255,255,0, 100)
                    if force.modulo > 4:
                        self._momentum.angle += self._twopi / 64.0

                else:
                    # left side
                    self._force_c = (255,0,255, 100)

                    if force.modulo > 4:
                        self._momentum.angle -= self._twopi / 64.0

    def draw(self, output):
        """Draw"""
        self._surf = output
        self._animate()
        sp_num = self._simple_angle
        shadow_v = Point(self._height, self._height / 2)
        shadow_v.round_to_int()

        p = self._centerp + self._force * 10
        p.round_to_int()
        try:
            #pygame.draw.aaline(output, self._force_c, self._centerp, p,  1)
            p = self._centerp + self._momentum * 15 + \
                self._momentum.normalized() * 15
            pygame.draw.aaline(output, (0,255,0, 255), self._centerp, p,  1)
        except Exception, e:
            pass

        output.blit(self.shadow_sprites[sp_num], self._tlp + shadow_v)
        output.blit(self.sprites[sp_num], self._tlp)


class FloatingVehicle(Vehicle):
    """Abstract class for floating vehicles"""

    def __init__(self, pos=None, network=None, vehicles=None):
        super(FloatingVehicle, self).__init__(pos=pos, network=network, vehicles=vehicles)
        self._height = 0
        self._flight_height = int(Get_Grid_Size() / 2)

    def _float(self):
        """Animate floatation"""
        self._anim_float += .15
        self._anim_float %= self._twopi
        self._height += math.sin(self._anim_float) / 6

        #self._height += randint(-1, 1) / 2.0
        if self._height < self._flight_height / 2:
            self._height = self._flight_height / 2
        elif self._height > self._flight_height * 2:
            self._height = self._flight_height * 2

    def _animate(self, action=None):
        """Animate"""
        self._anim_cnt += 1
        self._anim_cnt %= 500
        if random.random() > 0.95:
            self._anim_cnt += 1

        # random turns
        #if self._anim_cnt % 170 == 0 and self._status == 'go':
        #    self._momentum.angle += randint(-1, 1) / 9.0 * self._twopi
        #if self._anim_cnt % 10 == 0 and self._status == 'go':
        #self._momentum.angle += randint(-1, 1) / 90.0

        #if self._anim_cnt == 200:
        #    self._status = 'land'
        #elif self._anim_cnt == 300:
        #    self._status = 'lift'

        ## avoid obstacles
        #for r in self._net.rock_list + self._net.node_list:
        #    v = r._tlp - self._tlp
        #    dist = v.modulo
        #    if dist < Get_Grid_Size() * 3: # too close, do u-turn
        #        self._u_turn()
        #        return
        #    if dist < Get_Grid_Size() * 6: # try to steer
        #        pass
        #        #TODO

        # avoid getting out of the screen
        #if not (10 < self._tlp.x < 800) or \
        #    not (10 < self._tlp.y < 800):
        #        self._u_turn()
        #        return

        # lifting from ground
        if self._status == 'lift':
            # lift
            if self._height < self._flight_height:
                self._height += 2 # FIXME: was .2
            else:
                # wait
                self._anim_startstop_cnt += 1
                if self._anim_startstop_cnt > 10:
                    # go
                    self._anim_startstop_cnt = 0
                    self._status = 'go'

        # landing
        elif self._status == 'land':
            if self._momentum.modulo > .1:
                # slow down
                self._momentum.modulo -= .1
                self._drive()
                self._avoid()
            else:
                # land
                if self._height > 0:
                    self._height -= .2

        # driving
        elif self._status == 'go':
            self._avoid()
            # adjust speed
            if self._momentum.modulo != self.cruise_speed:
                self._momentum.modulo += (self.cruise_speed - self._momentum.modulo) / 50.0
            self._float()
            self._drive()

class Transport(FloatingVehicle):
    """Trasport floating ship"""
    def __init__(self, pos=None, network=None, vehicles=None):
        super(Transport, self).__init__(pos=pos, network=network, vehicles=vehicles)
        self.sprites = self._load_sprites("transport.png")
        self.shadow_sprites = self._load_sprites("transport_shadow.png")


class Tank(Vehicle):

    def __init__(self, pos=None, network=None, vehicles=None):
        super(Tank, self).__init__(pos=pos, network=network, vehicles=vehicles)
        self._vehicles = vehicles
        self.cruise_speed = 2
        self.turret_sprites = self._load_sprites("upper part ")
        self.body_sprites = self._load_sprites("tank groundpart")
        self._momentum = Point(1, 0)
        self._momentum.angle = random.random() * self._twopi

    def _load_sprites(self, fname):
        """Load movement sprites from a 3x3 mosaic"""
        sprites = []
        b = 0x61442b
        for n in xrange(32):
            #s = resource.Load_Image("tank/%s%04d.bmp" % (fname, n))
            fn = "tank/%s%04d.bmp" % (fname, n)
            from resource import Path
            fn = Path(fn)
            s = pygame.image.load(fn)
            s.set_colorkey((97, 68, 43))
            #s = pygame.Surface((20, 20), flags=pygame.SRCALPHA)
            s = pygame.transform.smoothscale(s, (40, 40))
            sprites.append(s)

        return sprites


    @property
    def _simple_angle(self):
        return int(31.5 - self._momentum.angle / self._twopi * 31)

    @property
    def _turret_angle(self):
        return int(15.5 - self._force.angle / self._twopi * 31) % 32

    def draw(self, output):
        """Draw"""
        self._surf = output
        self._animate()
        sp_num = self._simple_angle

        output.blit(self.body_sprites[sp_num], self._tlp)
        output.blit(self.turret_sprites[self._turret_angle], self._tlp)

    def _animate(self, action=None):
        """Animate"""
        self._anim_cnt += 1
        self._anim_cnt %= 500
        if random.random() > 0.95:
            self._anim_cnt += 1

        # random turns
        #if self._anim_cnt % 170 == 0 and self._status == 'go':
        #    self._momentum.angle += randint(-1, 1) / 9.0 * self._twopi
        #if self._anim_cnt % 10 == 0 and self._status == 'go':
        #self._momentum.angle += randint(-1, 1) / 90.0

        #if self._anim_cnt == 200:
        #    self._status = 'land'
        #elif self._anim_cnt == 300:
        #    self._status = 'lift'

        ## avoid obstacles
        #for r in self._net.rock_list + self._net.node_list:
        #    v = r._tlp - self._tlp
        #    dist = v.modulo
        #    if dist < Get_Grid_Size() * 3: # too close, do u-turn
        #        self._u_turn()
        #        return
        #    if dist < Get_Grid_Size() * 6: # try to steer
        #        pass
        #        #TODO

        # avoid getting out of the screen
        #if not (10 < self._tlp.x < 800) or \
        #    not (10 < self._tlp.y < 800):
        #        self._u_turn()
        #        return

        self._avoid()
        # adjust speed
        if self._momentum.modulo != self.cruise_speed:
            self._momentum.modulo += (self.cruise_speed - self._momentum.modulo) / 50.0
        self._drive()

class Well(Item):
    def __init__(self, (x,y), name="Well"):
        Item.__init__(self, name)
        self.pos = (x,y)
        self.draw_obj = draw_obj.Draw_Obj("well.png", 1)
        self.emits_steam = True

class Rock(Item):
    """Just a big rock, of random size"""
    def __init__(self, (x, y), size, name="Rock"):
        Item.__init__(self, name)
        self.pos = (x,y)
        self.rock_img = resource.Load_Image("rock.png")
        self.shadow_img = resource.Load_Image("rock_shadow.png")

        self._size = size
        width = int(self._size * Get_Grid_Size())

        ratio = float(self.rock_img.get_height()) / self.rock_img.get_width()
        height = int(width * ratio)
        # top-left, center, bottom-right, size in pixels
        self._sizep = scale_to = Point(width, height)
        self._brp = self._tlp + self._sizep
        self._centerp = self._tlp + self._sizep * .5
        self.rock_img = pygame.transform.smoothscale(self.rock_img, scale_to)
        self.shadow_img = pygame.transform.smoothscale(self.shadow_img, scale_to)
        self.shadow_img.set_alpha(50)

        self.quantity = self._size * DIFFICULTY.ROCK_QUANTITY
        self.reflexes = [
            # x (0 to 64), y, sequence value for each reflex
            [10, 30, randint(0, 128)],
            [32, 40, randint(0, 128)],
            [25, 15, randint(0, 128)],
            [30, 50, randint(0, 128)],
            [22, 25, randint(0, 128)],
        ]
        self.reflex_color = (255, 255, 255)

        # rock entry point (for digging)
        down = Point(0, self._sizep.y)
        self.entry_point = self._tlp + self._sizep * .3 + down * .4
        self.entry_point.round_to_int()

    def dig(self, distance):
        """Dig an amount of metal"""
        if self.quantity <= 0:
            return 0
        chunk = 1.5 / (distance + 1)
        chunk = min(self.quantity, chunk)
        self.quantity -= chunk
        return chunk

    # unused
    def Draw_Selected(self, output, highlight):
        ra = ( Get_Grid_Size() / 2 ) + 2
        pygame.draw.circle(output, highlight,
            Grid_To_Scr(self.pos), ra , 2 )
        return Grid_To_Scr_Rect(self.pos).inflate(ra,ra)

    def Draw(self, output):
        """Make the rock shine"""
        # print the rock
        p = self._tlp
        output.blit(self.shadow_img, p)
        output.blit(self.rock_img, p)

        # purge reflexes based on the amount of metal
        max_reflexes = self.quantity / 200
        if len(self.reflexes) > max_reflexes:
            self.reflexes.pop()

        # animate reflexes

        scale = self._sizep.modulo / 120.0
        for reflex in self.reflexes:
            # print a reflex
            reflex[2] += 1
            x, y, seq = reflex
            if seq < 32:
                alpha = seq * 8
            elif seq < 64:
                alpha = 512 - seq * 8
            else:
                alpha = 0

            if seq > 128:
                reflex[2] = 0

            if alpha > 255:
                alpha = 255

            p = self._tlp + Point(x, y) * scale
            p.round_to_int()
            col = self.reflex_color + (alpha,)
            col2 = self.reflex_color + (int(alpha * .8),)
            gfxdraw.pixel(output, p.x, p.y, col)
            gfxdraw.pixel(output, p.x + 1, p.y, col2)
            gfxdraw.pixel(output, p.x - 1, p.y, col2)
            gfxdraw.pixel(output, p.x, p.y + 1, col2)
            gfxdraw.pixel(output, p.x, p.y - 1, col2)


class Building(Item):
    def __init__(self, name):
        Item.__init__(self, name)
        self.health = 0
        self.complete = False
        self.was_once_complete = False
        self.max_health = 5 * HEALTH_UNIT 
        self.base_colour = (255,255,255)
        self.connection_value = 0
        self.other_item_stack = []
        self.popup_disappears_at = 0.0
        self.destroyed = False
        self.tech_level = 1
        self.owned_by_me = False


    def Exits(self):
        return []

    def Prepare_To_Die(self):
        self.popup_disappears_at = 0.0
        self.health = 0
        self.destroyed = True

    def Take_Damage(self, dmg_level=1):
        x = int(dmg_level * DIFFICULTY.DAMAGE_FACTOR)
        self.health -= x
        if self.health <= 0:
            self.Prepare_To_Die()
            return True
        return False

    def Begin_Upgrade(self):
        pass

    def Save(self, other_item):
        # Used for things that stack on top of other things,
        # e.g. steam maker on top of well
        assert isinstance(other_item, Item)
        assert other_item.pos == self.pos
        self.other_item_stack.append(other_item)

    def Restore(self):
        if len(self.other_item_stack) != 0:
            return self.other_item_stack.pop()
        else:
            return None

    def Is_Destroyed(self):
        return self.destroyed
    
    def Needs_Work(self):
        return ( self.max_health != self.health )
        
    def Is_Broken(self):
        return self.Needs_Work()

    def Do_Work(self):
        if not self.destroyed:
            if self.health < self.max_health:
                self.health += WORK_UNIT_SIZE
            if self.health >= self.max_health:
                self.health = self.max_health
                if self.was_once_complete:
                    # An upgrade or repair
                    sound.FX("double")
                else:
                    # Construction complete!
                    sound.FX("whoosh1")
                    #self.owned_by_me = True
                    #print 'constr compl', type(self)
                self.complete = True
                self.was_once_complete = True

    def Get_Popup_Items(self):
        return [ self.Get_Health_Meter() ]
    
    def Get_Health_Meter(self):
        return (self.health, (0,255,0), self.max_health, (255,0,0))

    def Draw_Popup(self, output):
        (x,y) = Grid_To_Scr(self.pos)
        x -= 16
        y -= 12
        r = stats.draw_popup_bar_meter(
            output,
            self.Get_Popup_Items(),
            (x, y),
            32, # width
            5, # height
            self.popup_alpha,
        )
        return r

    def Get_Tech_Level(self):            
        return ("Tech Level %d" % self.tech_level)

    def Get_Information(self):
        l = Item.Get_Information(self)
        h = (( self.health * 100 ) / self.max_health)
        h2 = (self.max_health - self.health)
        units = ""
        if h2 > 0:
            units = str(h2) + " more unit"
            if h2 != 1:
                units += "s"
            units += " req'd "

        if self.complete:
            if self.health == self.max_health:
                l += [ (self.Get_Diagram_Colour(), 15, "Operational") ]
            else:
                l += [ (self.Get_Diagram_Colour(), 15, "Damaged, " + str(h) + "% health"),
                       (None, None, self.Get_Health_Meter()),
                       ((128,128,128), 10, units + "to complete repairs")]

            l += [ ((128,128,0), 15, self.Get_Tech_Level()) ]
        else:
            if self.health > 0:
                l += [ (self.Get_Diagram_Colour(), 15, "Building, " + str(h) + "% done"),
                       (None, None, self.Get_Health_Meter()),
                       ((128,128,128), 10, units + "to finish building")]
            else:
                l += [ (self.Get_Diagram_Colour(), 15, "Not Built") ]

        if isinstance(self, City_Node):
            l.append((self.Get_Diagram_Colour(), 15,
                "Metal: %d" % int(self.metal_quantity)))

        return l
    
    def Get_Diagram_Colour(self):
        (r,g,b) = self.base_colour
        if self.complete:
            if self.health < self.max_health:
                g = ( self.health * g ) / self.max_health
                b = ( self.health * b ) / self.max_health
                if r < 128: r = 128
        else:
            if self.health > 0:
                r = ( self.health * r ) / self.max_health
                b = ( self.health * b ) / self.max_health
                if r < 128: r = 128
            else:
                r = g = b = 128
        return (r,g,b)

class Node(Building):
    def __init__(self,(x,y),name="Node", rocks=[]):
        Building.__init__(self,name)
        self.pipes = []
        self.pos = (x,y)
        self.max_health = NODE_HEALTH_UNITS * HEALTH_UNIT
        self.base_colour = (255,192,0)
        self.steam = Steam_Model()
        self._sp_finished = sprites.AnimatedSprite('node.anim')
        self._sp_venting = sprites.AnimatedSprite('node_venting.anim')
        self._sp_under_construction = sprites.AnimatedSprite(
            'node_under_construction.anim')
        self._sp_incomplete = sprites.Sprite('node_incomplete.png', 1.3)
        self.draw_obj = self._sp_incomplete
        self._hissing_started = 0
        self.conveyor_offset = 0
        self.metal_yield = 0
        self.max_rock_distance = INITIAL_NODE_EXCAVATION_DISTANCE
        self.rocks_nearby = self.locate_nearby_rocks(rocks)

    def locate_nearby_rocks(self, rocks):
        """Locate rocks close to this node
        Set sef.rocks_nearby to [(rock, distance), ... ]
        """
        maxd = self.max_rock_distance
        li = [(rock, distance(self.pos, rock.pos)) for rock in rocks]
        self.rocks_nearby = [t for t in li if t[1] < maxd]

    @property
    def is_connectable(self):
        """Check if the node can receive new pipes: either it's owned by
        the playerit never had an owner and there are no pipes connected to it
        """
        return self.owned_by_me or not self.pipes

    def Do_Work(self, broadcast_update=None, owned_by_me=True):
        """Do build/repair work on a node"""
        status = self.complete
        super(Node, self).Do_Work()
        # Update ownership if the Node has been completed now
        if status ^ self.complete and owned_by_me:
            self.owned_by_me = True
            log.debug('setting node %s as owned' % repr(self))
            if broadcast_update:
                broadcast_update(
                    item='node',
                    pos=self.pos,
                    event='new_owner',
                )

    def Begin_Upgrade(self):
        if self.tech_level >= NODE_MAX_TECH_LEVEL:
            New_Mail("Node cannot be upgraded further.")
            sound.FX("error")
        elif self.Needs_Work():
            New_Mail("Node must be operational before an upgrade can begin.")
            sound.FX("error")
        else:
            sound.FX("crisp")

            # Upgrade a node to get a higher capacity and more health.
            # More health means harder to destroy.
            # More capacity means your network is more resilient.
            self.tech_level += 1
            self.max_health += NODE_UPGRADE_WORK * HEALTH_UNIT
            self.complete = False
            self.steam.Capacity_Upgrade()

    def Steam_Think(self):
        nl = []
        for p in self.Exits():
            if p.valve_open and not p.Is_Broken():
                if p.n1 == self:
                    if not p.n2.Is_Broken():
                        nl.append((p.n2.steam, p.resistance))
                else:
                    if not p.n1.Is_Broken():
                        nl.append((p.n1.steam, p.resistance))

        nd = self.steam.Think(nl)
        for (p, current) in zip(self.Exits(), nd):
            # current > 0 means outgoing flow
            if current > 0.0:
                p.Flowing_From(self, current)

        if self.health == 0:
            # The node has never been built
            self.draw_obj = self._sp_incomplete
        elif self.Needs_Work():
            # It's being built or repaired
            self.draw_obj = self._sp_under_construction
        else:
            if self.steam.venting:
                # It's venting steam
                self.draw_obj = self._sp_venting
                # start hissing every 30 seconds
                now = time.time()
                if now - self._hissing_started > 30:
                    self._hissing_started = now
                    sound.FX("hissing_leak")
            else:
                # It's working normally
                self.draw_obj = self._sp_finished


    def Exits(self):
        return self.pipes

    def Get_Popup_Items(self):
        return Building.Get_Popup_Items(self) + [
                self.Get_Pressure_Meter() ]

    def Get_Pressure_Meter(self):
        return (int(self.Get_Pressure()), (100, 100, 255), 
                    int(self.steam.Get_Capacity()), (0, 0, 100))

    def Get_Information(self):
        infos = Building.Get_Information(self)
        infos.append(
            ((128,128,128), 15, "Steam pressure: %1.1f P" %
            self.steam.Get_Pressure())
        )
        infos.append((self.Get_Diagram_Colour(), 15,
                "Metal yield: %d" % int(self.metal_yield * 10)))
        return infos

    def Get_Pressure(self):
        return self.steam.Get_Pressure()

    def Draw_Selected(self, output, highlight):

        p = Point(Grid_To_Scr(self.pos))

        color = highlight + (100,)
        width, height = self.draw_ellipse(output, p, 1, color, 2)
        return Grid_To_Scr_Rect(self.pos).inflate(width, height)


    def Draw(self, output):
        """Draw node and conveyors to the closest rocks
        """
        self.conveyor_offset += .01
        self.conveyor_offset %= 1

        for rock, dist in self.rocks_nearby:
            np = Grid_To_Scr(self.pos)
            colour = (100,) * 3
            if self.metal_yield == 0:
                continue

            # Animate moving dots, in two ways
            np = Point(np)
            rp = rock.entry_point
            dist = np - rp

            if dist.modulo < 1: # No conveyors when the node is *in* the rock
                continue

            colour = (0, 0, 0, 230)
            for l in xrange(5):
                p = rp + dist / 5.0 * (l + self.conveyor_offset)
                p2 = rp + dist / 5.0 * (l + self.conveyor_offset + .15)
                pygame.draw.aaline(output, colour, p.tup, p2.tup, 1)

            # move the return line aside (left-hand traffic ;) )
            n = dist.orthogonal() * -2
            for l in xrange(5):
                p = np + n - dist / 5.0 * (l + self.conveyor_offset)
                p2 = np + n - dist / 5.0 * (l + self.conveyor_offset + .15)
                pygame.draw.aaline(output, colour, p.tup, p2.tup, 1)

        self.draw_obj.Draw(output, self.pos, (0,0))


    def Sound_Effect(self):
        sound.FX("node_rap")

class City_Node(Node):
    def __init__(self,(x,y),name="City"):
        Node.__init__(self,(x,y),name)
        self.base_colour = CITY_COLOUR
        self.avail_work_units = 1 
        self.city_upgrade = 0
        self.city_upgrade_start = 1
        self.draw_obj = draw_obj.Draw_Obj("city1.png", 3)
        self._sp_finished = self._sp_incomplete = self.draw_obj
        self.total_steam = 0
        self.metal_quantity = 50000 #FIXME
        self.metal_production = 0

    def Begin_Upgrade(self):
        # Upgrade a city for higher capacity
        # and more work units. Warning: upgraded city
        # will require more steam!
        #
        # Most upgrades use the health system as this
        # puts the unit out of action during the upgrade.
        # This isn't suitable for cities: you lose if your
        # city is out of action. We use a special system.
        if self.city_upgrade == 0:
            if self.tech_level < DIFFICULTY.CITY_MAX_TECH_LEVEL:
                sound.FX("mechanical_1")

                self.city_upgrade = self.city_upgrade_start = (
                    ( CITY_UPGRADE_WORK + ( self.tech_level * 
                    DIFFICULTY.CITY_UPGRADE_WORK_PER_LEVEL )) * HEALTH_UNIT )
                self.avail_work_units += 1 # Extra steam demand
            else:
                New_Mail("City is fully upgraded.")
                sound.FX("error")
        else:
            New_Mail("City is already being upgraded.")
            sound.FX("error")

    def Needs_Work(self):
        return ( self.city_upgrade != 0 )

    def Is_Broken(self):
        return False

    def Do_Work(self, broadcast_update=None, owned_by_me=True):
        if self.city_upgrade > 0:
            self.city_upgrade -= 1
            if self.city_upgrade == 0:
                self.tech_level += 1
                self.steam.Capacity_Upgrade()

                sound.FX("cityups")
                New_Mail("City upgraded to level %d of %d!" %
                    ( self.tech_level, DIFFICULTY.CITY_MAX_TECH_LEVEL ) )

    def Get_Avail_Work_Units(self):
        return self.avail_work_units

    def Get_Steam_Demand(self):
        return (( self.avail_work_units * 
                WORK_STEAM_DEMAND ) + STATIC_STEAM_DEMAND )

    def Get_Steam_Supply(self):
        supply = 0.0
        for pipe in self.pipes:
            if self == pipe.n1:
                supply -= pipe.current_n1_to_n2
            else:
                supply += pipe.current_n1_to_n2
            
        return supply

    def Get_Information(self):
        l = Node.Get_Information(self)
        if self.city_upgrade != 0:
            l.append( ((255,255,50), 12, "Upgrading...") )
            l.append( (None, None, self.Get_City_Upgrade_Meter()) )
        return l

    def Get_City_Upgrade_Meter(self):
        if self.city_upgrade == 0:
            return (0, (0,0,0), 1, (64,64,64))
        else:
            return (self.city_upgrade_start - self.city_upgrade, (255,255,50), 
                 self.city_upgrade_start, (64,64,64))

    def Steam_Think(self):
        x = self.Get_Steam_Demand()
        self.total_steam += x
        self.steam.Source(- x)
        Node.Steam_Think(self)

    def Draw(self, output):
        Node.Draw(self, output)

    def Get_Popup_Items(self):
        return [ self.Get_City_Upgrade_Meter() ,
                self.Get_Pressure_Meter() ]

    def Take_Damage(self, dmg_level=1):  # Can't destroy a city.
        return False

    def Draw_Selected(self, output, highlight):
        p = Point(Grid_To_Scr(self.pos))
        color = highlight + (100,)
        width, height = self.draw_ellipse(output, p, 2, color, 2)
        return Grid_To_Scr_Rect(self.pos).inflate(width, height)

    def Get_Tech_Level(self):
        return Building.Get_Tech_Level(self) + (" of %d" % DIFFICULTY.CITY_MAX_TECH_LEVEL )

    def Sound_Effect(self):
        sound.FX("computer")


class Well_Node(Node):
    def __init__(self,(x,y),name="Steam Maker", rocks=[]):
        Node.__init__(self,(x,y),name)
        self.base_colour = (255,0,192)
        self._sp_finished = draw_obj.Draw_Obj("maker.png", 1.11)
        self._sp_incomplete = draw_obj.Draw_Obj("maker_u.png", 1)
        self.draw_obj = self._sp_incomplete
        self.emits_steam = True
        self.production = 0


    def Steam_Think(self):
        if not self.Needs_Work():
            self.production = (DIFFICULTY.BASIC_STEAM_PRODUCTION + (self.tech_level * 
                    DIFFICULTY.STEAM_PRODUCTION_PER_LEVEL))
            self.steam.Source(self.production)
        else:
            self.production = 0
        Node.Steam_Think(self)

    def Get_Information(self):
        return Node.Get_Information(self) + [
            (self.base_colour, 15, 
                "Steam production: %1.1f U" % self.production) ]

    def Sound_Effect(self):
        sound.FX("steam_maker")


class Pipe(Building):
    def __init__(self,n1,n2,name="Pipe"):
        Building.__init__(self,name)
        assert n1 != n2
        self.valve_open = True
        n1.pipes.append(self)
        n2.pipes.append(self)
        self.n1 = n1
        self.n2 = n2
        (x1,y1) = n1.pos
        (x2,y2) = n2.pos
        self.pos = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.length = math.hypot(x1 - x2, y1 - y2)
        self.max_health = int(self.length + 1) * HEALTH_UNIT
        self.base_colour = (0,255,0)
        self.resistance = ( self.length + 2.0 ) * RESISTANCE_FACTOR
        self.current_n1_to_n2 = 0.0

        self.dot_drawing_offset = 0
        self.dot_positions = []
        sound.FX("pipe_construction")

    def Do_Work(self, broadcast_update=None):
        """Do build/repair work on a pipe"""
        status = self.complete
        super(Pipe, self).Do_Work()
        # Update ownership if the Pipe has been completed now
        if status ^ self.complete:
            log.debug('pipe finished owned')
            if self.n1.owned_by_me or self.n2.owned_by_me:
                log.debug('setting pipe owned')
                self.owned_by_me = True
                if broadcast_update:
                    broadcast_update(
                        item='pipe',
                        pos=self.pos,
                        event='new_owner',
                    )

    def Begin_Upgrade(self):
        if self.tech_level >= PIPE_MAX_TECH_LEVEL:
            New_Mail("Pipe cannot be upgraded further.")
            sound.FX("error")
        elif self.Needs_Work():
            New_Mail("Pipe must be operational before an upgrade can begin.")
            sound.FX("error")
        else:
            sound.FX("pipe_upgrade")
            # Upgrade a pipe for lower resistance and more health.
            self.tech_level += 1
            self.max_health += int( PIPE_UPGRADE_WORK_FACTOR * 
                        self.length * HEALTH_UNIT )
            self.complete = False
            self.resistance *= PIPE_UPGRADE_RESISTANCE_FACTOR

    def Exits(self):
        return [self.n1, self.n2]

    def Flowing_From(self, node, current):
        if node == self.n1:
            self.current_n1_to_n2 = current
        elif node == self.n2:
            self.current_n1_to_n2 = - current
        else:
            assert False

    def Take_Damage(self, dmg_level=1):
        # Pipes have health proportional to their length.
        # To avoid a rules loophole, damage inflicted on
        # pipes is multiplied by their length. Pipes are
        # a very soft target.
        return Building.Take_Damage(self, dmg_level * (self.length + 1.0))

    def Draw_Mini(self, output, (x,y) ):
        (x1,y1) = Grid_To_Scr(self.n1.pos)
        (x2,y2) = Grid_To_Scr(self.n2.pos)
        x1 -= x ; x2 -= x
        y1 -= y ; y2 -= y

        if self.Needs_Work():
            c = (255,0,0)
        else:
            c = self.Get_Diagram_Colour()

        pygame.draw.line(output, c, (x1,y1), (x2,y2), 2)

        if not self.Needs_Work():
            mx = ( x1 + x2 ) / 2
            my = ( y1 + y2 ) / 2
            if output.get_rect().collidepoint((mx,my)):
                info_text = "%1.1f U" % abs(self.current_n1_to_n2)
                info_surf = stats.Get_Font(12).render(info_text, True, c)
                r2 = info_surf.get_rect()
                r2.center = (mx,my)
                r = Rect(r2)
                r.width += 4
                r.center = (mx,my)
                pygame.draw.rect(output, (0, 40, 0), r)
                output.blit(info_surf, r2.topleft)


    def Draw(self,output):
        (x1,y1) = Grid_To_Scr(self.n1.pos)
        (x2,y2) = Grid_To_Scr(self.n2.pos)
        if self.Needs_Work():
            # Plain red line
            pygame.draw.line(output, (255,0,0), (x1,y1), (x2,y2), 3)
            self.dot_drawing_offset = 0
            return


        # Dark green backing line:
        if self.valve_open:
            colour = (32,128,20)
        else:
            colour = (22,90,10)

        pygame.draw.line(output, colour, (x1,y1), (x2,y2), 3)

        if self.current_n1_to_n2 == 0.0:
            return
            
        r = Rect(0,0,1,1)
        for pos in self.dot_positions:
            r.center = pos
            output.fill(colour, r)

        # Thanks to Acidd_UK for the following suggestion.
        dots = int(( self.length * 0.3 ) + 1.0)
        positions = dots * self.SFACTOR

        pos_a = (x1, y1 + 1)
        pos_b = (x2, y2 + 1)
        interp = self.dot_drawing_offset
        colour = (80, 255, 80) # bright green dots

        self.dot_positions = [ 
            extra.Partial_Vector(pos_a, pos_b, (interp, positions))
            for interp in range(self.dot_drawing_offset, positions, 
                    self.SFACTOR) ]

        for pos in self.dot_positions:
            r.center = pos
            output.fill(colour, r)
    
    # Tune these to alter the speed of the dots.
    SFACTOR = 512
    FUTZFACTOR = 4.0 * 35.0

    def Frame_Advance(self, frame_time):
        if self.valve_open:
            self.dot_drawing_offset += int(self.FUTZFACTOR * 
                    frame_time * self.current_n1_to_n2)

        if self.dot_drawing_offset < 0:
            self.dot_drawing_offset = (
                self.SFACTOR - (( - self.dot_drawing_offset ) % self.SFACTOR ))
        else:
            self.dot_drawing_offset = self.dot_drawing_offset % self.SFACTOR

    def Make_Ready_For_Save(self):
        self.dot_positions = []

    def __Draw_Original(self, output):
        (x1,y1) = Grid_To_Scr(self.n1.pos)
        (x2,y2) = Grid_To_Scr(self.n2.pos)
        if self.Needs_Work():
            c = (255,0,0)
        else:
            c = self.Get_Diagram_Colour()
        pygame.draw.line(output, c, (x1,y1), (x2,y2), 2)

    def Draw_Selected(self, output, highlight):
        p1 = Grid_To_Scr(self.n1.pos)
        p2 = Grid_To_Scr(self.n2.pos)
        pygame.draw.line(output, highlight, p1, p2, 5)
        #self.Draw(output) # Already done elsewhere.

        return Rect(p1,(1,1)).union(Rect(p2,(1,1))).inflate(7,7)

    def Get_Information(self):
        return Building.Get_Information(self) + [
            ((128,128,128), 15, "%1.1f km" % self.length) ,
            ((128,128,128), 15, "Flow rate: %1.1f U" % abs(self.current_n1_to_n2) ) ]

    def Sound_Effect(self):
        sound.FX("pipe_flow")

    def toggle_valve(self):
        """Open/close steam valve"""
        self.valve_open = not self.valve_open
        sound.FX("valve_squeak")
