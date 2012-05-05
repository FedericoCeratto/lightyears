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
from steam_model import Steam_Model
import time
from mail import New_Mail


class Item:
    def __init__(self, name):
        self.pos = None
        self.name_type = name
        self.draw_obj = None
        self.emits_steam = False
        self.tutor_special = False

    def Draw(self, output):
        self.draw_obj.Draw(output, self.pos, (0,0))

    def Draw_Mini(self, output, soffset):
        self.draw_obj.Draw(output, self.pos, soffset)

    def Draw_Selected(self, output, highlight):
        return None

    def Draw_Popup(self, output):
        return None

    def Get_Information(self):
        return [ ((255,255,0), 20, self.name_type) ]

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


class Well(Item):
    def __init__(self, (x,y), name="Well"):
        Item.__init__(self, name)
        self.pos = (x,y)
        self.draw_obj = draw_obj.Draw_Obj("well.png", 1)
        self.emits_steam = True

class Rock(Item):
    """Just a big rock, of random size"""
    def __init__(self, (x,y), name="Rock"):
        Item.__init__(self, name)
        self.pos = (x,y)
        size = randint(1, 3)
        self.draw_obj = draw_obj.Draw_Obj("rock.png", size)
        self.quantity = size * DIFFICULTY.ROCK_QUANTITY + \
            randint(1, DIFFICULTY.ROCK_QUANTITY)
        self.reflexes = [
            # x (0 to 64), y, sequence value for each reflex
            [10, 30, randint(0, 128)],
            [32, 40, randint(0, 128)],
            [25, 15, randint(0, 128)],
            [30, 50, randint(0, 128)],
            [22, 25, randint(0, 128)],
        ]

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
        self.draw_obj.Draw(output, self.pos, (0,0))

        max_reflexes = self.quantity / 200
        if len(self.reflexes) > max_reflexes:
            self.reflexes.pop()

        size = self.draw_obj.key[1] * Get_Grid_Size() # in pixels
        rock_topleft = Point(Grid_To_Scr(self.pos)) - Point(size, size) / 2
        scale = (size / 64.0)
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
            p = rock_topleft + Point(x,y) * scale
            p.round_to_int()
            col = (255, 255, 255, alpha)
            col2 = (255, 255, 255, int(alpha * .7))
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


    def Exits(self):
        return []

    def Prepare_To_Die(self):
        self.popup_disappears_at = 0.0
        self.health = 0
        self.destroyed = True

    def Take_Damage(self, dmg_level=1):
        x = int(dmg_level * DIFFICULTY.DAMAGE_FACTOR)
        self.health -= x
        if ( self.health <= 0 ):
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
        if ( len(self.other_item_stack) != 0 ):
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
        if ( not self.destroyed ):
            if ( self.health < self.max_health ):
                self.health += WORK_UNIT_SIZE
            if ( self.health >= self.max_health ):
                self.health = self.max_health
                if ( self.was_once_complete ):
                    # An upgrade or repair
                    sound.FX("double")
                else:
                    # Construction complete!
                    sound.FX("whoosh1")
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
        return stats.draw_popup_bar_meter(output, self.Get_Popup_Items(), (x,y), 32, 5)

    def Get_Tech_Level(self):            
        return ("Tech Level %d" % self.tech_level)

    def Get_Information(self):
        l = Item.Get_Information(self)
        h = (( self.health * 100 ) / self.max_health)
        h2 = (self.max_health - self.health)
        units = ""
        if ( h2 > 0 ):
            units = str(h2) + " more unit"
            if ( h2 != 1 ):
                units += "s"
            units += " req'd "

        if ( self.complete ):
            if ( self.health == self.max_health ):
                l += [ (self.Get_Diagram_Colour(), 15, "Operational") ]
            else:
                l += [ (self.Get_Diagram_Colour(), 15, "Damaged, " + str(h) + "% health"),
                       (None, None, self.Get_Health_Meter()),
                       ((128,128,128), 10, units + "to complete repairs")]

            l += [ ((128,128,0), 15, self.Get_Tech_Level()) ]
        else:
            if ( self.health > 0 ):
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
        if ( self.complete ):
            if ( self.health < self.max_health ):
                g = ( self.health * g ) / self.max_health
                b = ( self.health * b ) / self.max_health
                if ( r < 128 ): r = 128
        else:
            if ( self.health > 0 ):
                r = ( self.health * r ) / self.max_health
                b = ( self.health * b ) / self.max_health
                if ( r < 128 ): r = 128
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
        self.draw_obj_finished = draw_obj.Draw_Obj("node.png", 1)
        self.draw_obj_venting = draw_obj.Draw_Obj("node_venting.png", 1)
        self.draw_obj_incomplete = draw_obj.Draw_Obj("node_u.png", 1)
        self.draw_obj = self.draw_obj_incomplete
        self._hissing_started = 0
        self.conveyor_offset = 0
        self.max_rock_distance = INITIAL_NODE_EXCAVATION_DISTANCE
        self.rocks_nearby = self.locate_nearby_rocks(rocks)

    def locate_nearby_rocks(self, rocks):
        """Locate rocks close to this node
        Set sef.rocks_nearby to [(rock, distance), ... ]
        """
        maxd = self.max_rock_distance
        li = [(rock, distance(self.pos, rock.pos)) for rock in rocks]
        self.rocks_nearby = [t for t in li if t[1] < maxd]

    def Begin_Upgrade(self):
        if ( self.tech_level >= NODE_MAX_TECH_LEVEL ):
            New_Mail("Node cannot be upgraded further.")
            sound.FX("error")
        elif ( self.Needs_Work() ):
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
                if ( p.n1 == self ):
                    if ( not p.n2.Is_Broken() ):
                        nl.append((p.n2.steam, p.resistance))
                else:
                    if ( not p.n1.Is_Broken() ):
                        nl.append((p.n1.steam, p.resistance))

        nd = self.steam.Think(nl)
        for (p, current) in zip(self.Exits(), nd):
            # current > 0 means outgoing flow
            if ( current > 0.0 ):
                p.Flowing_From(self, current)

        if ( self.Is_Broken() ):
            self.draw_obj = self.draw_obj_incomplete
        else:
            if self.steam.venting:
                self.draw_obj = self.draw_obj_venting
                # start hissing every 30 seconds
                now = time.time()
                if now - self._hissing_started > 30:
                    self._hissing_started = now
                    sound.FX("hissing_leak")
            else:
                self.draw_obj = self.draw_obj_finished


    def Exits(self):
        return self.pipes

    def Get_Popup_Items(self):
        return Building.Get_Popup_Items(self) + [
                self.Get_Pressure_Meter() ]

    def Get_Pressure_Meter(self):
        return (int(self.Get_Pressure()), (100, 100, 255), 
                    int(self.steam.Get_Capacity()), (0, 0, 100))

    def Get_Information(self):
        return Building.Get_Information(self) + [
            ((128,128,128), 15, "Steam pressure: %1.1f P" % self.steam.Get_Pressure()) ]

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
            rp = Grid_To_Scr(rock.pos)
            colour = (100,) * 3
            pygame.draw.aaline(output, colour, np, rp, 1)
            if rock.quantity == 0:
                continue

            np = Point(np)
            rp = Point(rp)
            dist = np - rp
            colour = (0,) * 3
            for l in xrange(5):
                p = rp + dist / 5.0 * (l + self.conveyor_offset)
                p2 = rp + dist / 5.0 * (l + self.conveyor_offset + .2)
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
        self.draw_obj_finished = self.draw_obj_incomplete = self.draw_obj
        self.total_steam = 0
        self.metal_quantity = 500

    def Begin_Upgrade(self):
        # Upgrade a city for higher capacity
        # and more work units. Warning: upgraded city
        # will require more steam!
        #
        # Most upgrades use the health system as this
        # puts the unit out of action during the upgrade.
        # This isn't suitable for cities: you lose if your
        # city is out of action. We use a special system.
        if ( self.city_upgrade == 0 ):
            if ( self.tech_level < DIFFICULTY.CITY_MAX_TECH_LEVEL ):
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

    def Do_Work(self):
        if ( self.city_upgrade > 0 ):
            self.city_upgrade -= 1
            if ( self.city_upgrade == 0 ):
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
            if ( self == pipe.n1 ):
                supply -= pipe.current_n1_to_n2
            else:
                supply += pipe.current_n1_to_n2
            
        return supply

    def Get_Information(self):
        l = Node.Get_Information(self)
        if ( self.city_upgrade != 0 ):
            l.append( ((255,255,50), 12, "Upgrading...") )
            l.append( (None, None, self.Get_City_Upgrade_Meter()) )
        return l

    def Get_City_Upgrade_Meter(self):
        if ( self.city_upgrade == 0 ):
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
        r = Grid_To_Scr_Rect(self.pos).inflate(CITY_BOX_SIZE,CITY_BOX_SIZE)
        pygame.draw.rect(output, highlight,r,2)
        return r.inflate(2,2)

    def Get_Tech_Level(self):            
        return Building.Get_Tech_Level(self) + (" of %d" % DIFFICULTY.CITY_MAX_TECH_LEVEL )

    def Sound_Effect(self):
        sound.FX("computer")


class Well_Node(Node):
    def __init__(self,(x,y),name="Steam Maker", rocks=[]):
        Node.__init__(self,(x,y),name)
        self.base_colour = (255,0,192)
        self.draw_obj_finished = draw_obj.Draw_Obj("maker.png", 1)
        self.draw_obj_incomplete = draw_obj.Draw_Obj("maker_u.png", 1)
        self.draw_obj = self.draw_obj_incomplete
        self.emits_steam = True
        self.production = 0


    def Steam_Think(self):
        if ( not self.Needs_Work() ):
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
        self.draw_obj_valve_open = draw_obj.Draw_Obj("valve_open.png", 1)
        self.draw_obj_valve_closed = draw_obj.Draw_Obj("valve_closed.png", 1)
        self.draw_obj = self.draw_obj_valve_closed
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

    def Begin_Upgrade(self):
        if ( self.tech_level >= PIPE_MAX_TECH_LEVEL ):
            New_Mail("Pipe cannot be upgraded further.")
            sound.FX("error")
        elif ( self.Needs_Work() ):
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
        if ( node == self.n1 ):
            self.current_n1_to_n2 = current
        elif ( node == self.n2 ):
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

        if ( self.Needs_Work() ):
            c = (255,0,0)
        else:
            c = self.Get_Diagram_Colour()

        pygame.draw.line(output, c, (x1,y1), (x2,y2), 2)

        if ( not self.Needs_Work() ):
            mx = ( x1 + x2 ) / 2
            my = ( y1 + y2 ) / 2
            if ( output.get_rect().collidepoint((mx,my)) ):
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
        if ( self.Needs_Work() ):
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

        if ( self.current_n1_to_n2 == 0.0 ):
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

        if ( self.dot_drawing_offset < 0 ):
            self.dot_drawing_offset = (
                self.SFACTOR - (( - self.dot_drawing_offset ) % self.SFACTOR ))
        else:
            self.dot_drawing_offset = self.dot_drawing_offset % self.SFACTOR

    def Make_Ready_For_Save(self):
        self.dot_positions = []

    def __Draw_Original(self, output):
        (x1,y1) = Grid_To_Scr(self.n1.pos)
        (x2,y2) = Grid_To_Scr(self.n2.pos)
        if ( self.Needs_Work() ):
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
