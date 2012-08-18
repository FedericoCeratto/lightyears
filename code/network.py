# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

# Sorry, this isn't anything to do with IP: the Network is 
# the steam transport network.

import math , random , time , sound

import extra
from map_items import *
from primitives import *
from mail import New_Mail
import math

from multiplayer import UserException

from logging import getLogger
log = getLogger(__name__)

def is_too_close(pos, li, d):
    """Check if item position is too close to any element from li
    """
    for other in li:
        if hasattr(other, 'pos'):
            other = other.pos
        if distance(pos, other) < d:
            return True

    return False

def get_closest(pos, li):
    """Get the closest element from a list"""
    dists = dict((distance(pos, i), i) for i in li)
    min_dist = min(dists)
    return dists[min_dist]

def rand_pos(margin):
    """Pick a random x,y gpos"""
    (mx, my) = GRID_SIZE
    return (
        random.randint(margin, mx - margin),
        random.randint(margin, my - margin)
    )

def generate_cities(max_num, margin, min_dist):
    """Generate cities at random locations"""
    cities = []
    # split the may by N x N rectangles, so that each quadrant will contain
    # one city at maximum
    N = math.ceil(max_num ** (.5))
    used_quadrants = set()
    cnt = 0
    while len(cities) < max_num and cnt < 100:
        pos = rand_pos(margin)
        quad = (int(pos[0] / N), int(pos[1] / N))
        # do not put 2 cities in the same quadrant
        if quad in used_quadrants:
            continue
        # keep distance between cities
        if is_too_close(pos, cities, min_dist):
            continue

        cities.append(pos)
        used_quadrants.add(quad)

    return cities

def generate_map(num_cities, min_dist_between_cities=12):
    """Generate map items randomly"""
    (x,y) = GRID_CENTRE
    (mx, my) = GRID_SIZE
    rocks = []
    wells = []

    # Cities
    if num_cities == 1:
        cities = [GRID_CENTRE, ]
    else:
        cities = generate_cities(num_cities, 4, min_dist_between_cities)

    # Create one well close to each city
    for c in cities:
        pos = (c[0] + 5, c[1] + random.randint(-3,3))
        wells.append(pos)

    # Other wells
    while len(wells) < len(cities) + 10:
        pos = rand_pos(2)

        # keep distance from the cities
        if is_too_close(pos, cities, 10):
            continue
        # keep distance from other wells
        if is_too_close(pos, wells, 1):
            continue

        wells.append(pos)

    # Rocks
    cnt = 0
    while len(rocks) < 10 and cnt < 100:
        cnt += 1
        pos = rand_pos(2)
        size = 1 + 5 * random.random()
        # keep distance from wells
        if is_too_close(pos, wells, int(size/8)):
            continue
        # keep distance from the cities
        if is_too_close(pos, cities, 9):
            continue
        # keep distance from other rocks
        rocks_pos = [p for p, s in rocks]
        if is_too_close(pos, rocks_pos, int(size/8)):
            continue

        rocks.append((pos, size))

    return cities, rocks, wells

class Network(object):
    def __init__(self, teaching, multiplayer):
        self._multiplayer = multiplayer
        self.ground_grid = dict()
        self.pipe_grid = dict()
        self.well_list = []
        self.node_list = []
        self.pipe_list = []
        self.rock_list = []
        self.cities_list = []

        # UI updates required?
        self.dirty = False
    
        # Popup health meters may appear
        self.popups = set([])


        if multiplayer is None:
            cities, rocks, wells = generate_map(1)
        else:
            cities, rocks, wells = multiplayer.get_static_map()
            log.debug(repr(cities))

        # Place wells
        if teaching:
            for i in xrange(10):
                self.Make_Well(teaching)
        else:
            for wgpos in wells:
                self.Add_Grid_Item(Well(wgpos))

        for c in cities:
            # create city
            cn = City_Node(c)
            self.Add_Finished_Node(cn)

            # create closest well
            wgpos = get_closest(c, wells)
            w = Well(wgpos)
            self.Add_Grid_Item(w)
            wn = Well_Node(wgpos)
            self.Add_Finished_Node(wn)
            wn.tutor_special = True

            # Pipe links the two
            self.Add_Pipe(cn, wn)
            pipe = cn.pipes[-1]
            pipe.health = pipe.max_health
            if self._multiplayer:
                pipe.Do_Work(broadcast_update=self._multiplayer.broadcast)
            else:
                pipe.Do_Work()

            # Set hub and update ownership
            if self._multiplayer and c != self._multiplayer.city:
                pass # This City is owned by another player
            else:
                # Set city as owned hub
                self.hub = cn
                self.hub.owned_by_me = True
                pipe.owned_by_me = True
                wn.owned_by_me = True


        self.connection_value = 1
        self.Work_Pulse(0) # used to make connection map

        for pos, size in rocks:
            self.rock_list.append(Rock(pos, size))

        # sort rock_list by "y" value, to be able to draw them in sequence
        # without incorrect overlapping
        self.rock_list.sort(key=lambda r: r.entry_point[1])

        for node in self.node_list:
            node.locate_nearby_rocks(self.rock_list)


    def Add_Finished_Node(self, node):
        if self._multiplayer:
            self._multiplayer.set_finished_node(node.pos)

        node.health = node.max_health
        if self._multiplayer:
            node.Do_Work(broadcast_update=self._multiplayer.broadcast)
        else:
            node.Do_Work()
        node.complete = True
        self.Add_Grid_Item(node)
        node.locate_nearby_rocks(self.rock_list)

    def Add_Grid_Item(self, item, inhibit_effects=False):
        gpos = item.pos
        if ( item.Is_Destroyed() ):
            if ( not inhibit_effects ):
                New_Mail("Item is destroyed.")
            return False

        if ( self.pipe_grid.has_key(gpos) ):
            # There might be a pipe in the way. Then again,
            # it may have been destroyed already.
            for pipe in self.pipe_grid[ gpos ]:
                if ( pipe.Is_Destroyed() ):
                    continue

                if ( extra.Intersect_Grid_Square(gpos, 
                            (pipe.n1.pos, pipe.n2.pos)) ):
                    if ( not inhibit_effects ):
                        New_Mail("Can't build there - pipe in the way!")
                        sound.FX("error")
                    return False

        if (( self.ground_grid.has_key(gpos) )
        and ( isinstance(self.ground_grid[ gpos ], Building) )):
            if ( not inhibit_effects ):
                New_Mail("Can't build there - building in the way!")
                sound.FX("error")
            return False

        if ( isinstance(item, Node) ):
            self.node_list.append(item)
            if ( self.ground_grid.has_key( gpos )):
                item.Save(self.ground_grid[ gpos ])
            self.ground_grid[ gpos ] = item
            item.locate_nearby_rocks(self.rock_list)
        elif isinstance(item, Well):
            self.well_list.append(item)
            self.ground_grid[ gpos ] = item
        else:
            assert False # unknown type!

        return True

    def Is_Connected(self, node):
        assert isinstance(node, Building)
        return ( node.connection_value == self.connection_value )

    def Work_Pulse(self, work_points):
        # Connection map is built up. Process is
        # recursive: a wavefront spreads out across the net.
        #
        # At the same time, find the first node that needs work doing,
        # and do work at it.
        used = 0
        now = set([ self.hub ])
        self.connection_value += 1
        cv = self.connection_value
        while ( len(now) != 0 ):
            next = set([])
            for node in now:
                if ( node.connection_value < cv ):
                    if (( work_points > 0 ) and node.Needs_Work() ):
                        if self._multiplayer:
                            node.Do_Work(broadcast_update=self._multiplayer.broadcast)
                        else:
                            node.Do_Work()
                        self.Popup(node)
                        work_points -= 1
                        used += 1
                    node.connection_value = cv
                    next |= set(node.Exits())
            now = next
        return used

    def dig_metal(self):
        """For each existing node close to a rock, extract metal and update
        the available metal counter in the city node
        """
        self.hub.metal_production = 0 # total production
        for node in self.node_list:
            node.metal_yield = 0
            if self.Is_Connected(node):
                for rock, distance in node.rocks_nearby:
                    extracted = rock.dig(distance)
                    self.hub.metal_quantity += extracted
                    self.hub.metal_production += extracted
                    node.metal_yield += extracted

    def use_metal(self, building_type):
        """Check if enough metal is available to build something.
        If so, decrease the remaining metal.
        """
        costs = {
            'up_node': 50,
            'node': 75,
            'well': 25,
        }
        cost = costs.get(building_type, 40)
        if self.hub.metal_quantity > cost:
            self.hub.metal_quantity -= cost
            return cost

        New_Mail("Insufficient metal: %s metal units required." % cost)
        return None

    def metal_available(self, building_type):
        """Check if enough metal is available to build something.
        If so, decrease the remaining metal.
        """
        costs = {
            'up_node': 50,
            'node': 75,
            'well': 25,
        }
        cost = costs.get(building_type, 40)
        if self.hub.metal_quantity > cost:
            return True

        New_Mail("Insufficient metal: %s metal units required." % cost)
        return False

    def is_closed_to_an_owned_node(self, gpos):
        """Check if a point is in proximity to any player-owned node."""
        for n in self.node_list:
            if n.owned_by_me:
                if distance(n.pos, gpos) < self._multiplayer._max_building_distance:
                    return True

        return False

    def Popup(self, node):
        if ( node != None ):
            self.popups |= set([node])
            node.popup_disappears_at = time.time() + 4.0

    def Expire_Popups(self):
        t = time.time()
        remove = set([])
        for node in self.popups:
            if ( node.popup_disappears_at <= t ):
                remove |= set([node])
        self.popups -= remove

    def Steam_Think(self):
        for n in self.node_list:
            n.Steam_Think()


    def Add_Pipe(self, n1, n2):

        if ( n1.Is_Destroyed() or n2.Is_Destroyed() ):
            sound.FX("error")
            New_Mail("Nodes are destroyed.")
            return False

        # What's in the pipe's path? 
        path = extra.More_Accurate_Line(n1.pos, n2.pos)
       
        other_pipes = set([])
        other_items = set([])
        for gpos in path:
            if ( self.pipe_grid.has_key(gpos) ):
                other_pipes |= set(self.pipe_grid[ gpos ])
            elif ( self.ground_grid.has_key(gpos) ):
                other_items |= set([self.ground_grid[ gpos ]])
        other_items -= set([n1,n2])
        if ( len(other_items) != 0 ):
            sound.FX("error")
            New_Mail("Pipe collides with other items.")
            return False

        for p in other_pipes:
            if ( not p.Is_Destroyed () ):
                if ((( p.n1 == n1 ) and ( p.n2 == n2 ))
                or (( p.n1 == n2 ) and ( p.n2 == n1 ))):
                    sound.FX("error")
                    New_Mail("There is already a pipe there.")
                    return False
                if ( intersect.Intersect((p.n1.pos,p.n2.pos),
                            (n1.pos,n2.pos)) != None ):
                    sound.FX("error")
                    New_Mail("That crosses an existing pipe.")
                    return False

        for r in self.rock_list:
            # Check for collisions with rocks by modeling each rock with
            # a big X (urgh!) Better collisions could be performed by using
            # the Sprite class
            lower_left =  (r.pos[0] - 1, r.pos[1] - 1)
            lower_right = (r.pos[0] - 1, r.pos[1] + 1)
            upper_right = (r.pos[0] + 1, r.pos[1] + 1)
            upper_left =  (r.pos[0] + 1, r.pos[1] - 1)
            if intersect.Intersect((lower_left, upper_right), (n1.pos, n2.pos)):
                sound.FX("error")
                New_Mail("Pipe collides with a rock.")
                return False
            if intersect.Intersect((lower_right, upper_left), (n1.pos, n2.pos)):
                sound.FX("error")
                New_Mail("Pipe collides with a rock.")
                return False

        if self._multiplayer:
            try:
                self._multiplayer.add_pipe((n1.pos, n2.pos))
            except UserException, e:
                log.debug(e)
                return False

        sound.FX("bamboo1")
        pipe = Pipe(n1, n2)
        self.pipe_list.append(pipe)

        for gpos in path:
            if ( not self.pipe_grid.has_key(gpos) ):
                self.pipe_grid[ gpos ] = [pipe]
            else:
                self.pipe_grid[ gpos ].append(pipe)
        return True

    def Get_Pipe(self, gpos):
        if ( not self.pipe_grid.has_key(gpos) ):
            return None
        l = self.pipe_grid[ gpos ]

        # Remove destroyed pipes
        l2 = [ pipe for pipe in l if not pipe.Is_Destroyed() ]

        # Did it change? Save it again if it did,
        # to save future recomputation.
        if ( len(l2) != len(l) ):
            self.pipe_grid[ gpos ] = l = l2

        if ( len(l) == 0 ):
            return None
        elif ( len(l) == 1 ):
            return l[ 0 ]
        else:
            # Juggle list
            out = l.pop(0)
            l.append(out)
            return out

    def Pipe_Possible(self, (x1,y1), (x2,y2)):
        # no restrictions
        return True
       
    def Destroy(self, node, by=None):
        if ( isinstance(node, Pipe) ):
            self.__Destroy_Pipe(node)
            return

        if (( node == self.hub )
        or ( not isinstance(node, Building) )):
            return # indestructible

        sound.FX("destroy")

        if ( isinstance(node, Node) ):
            # work on a copy, as __Destroy_Pipe will change the list.
            pipe_list = [ pipe for pipe in node.pipes ]
            for pipe in pipe_list:
                self.__Destroy_Pipe(pipe)

        gpos = node.pos
        if ( not self.ground_grid.has_key( gpos ) ):
            return # not on map
        if ( self.ground_grid[ gpos ] != node ):
            return # not on map (something else is there)

        self.dirty = True

        if ( by != None ):
            New_Mail(node.name_type + " destroyed by " + by + ".")
        

        node.Prepare_To_Die()
        self.__List_Destroy(self.node_list, node)
        rnode = node.Restore()

        if ( rnode == None ):
            del self.ground_grid[ gpos ]
        else:
            self.ground_grid[ gpos ] = rnode
        
    def __Destroy_Pipe(self, pipe):
        self.dirty = True
        pipe.Prepare_To_Die()
        self.__List_Destroy(self.pipe_list, pipe)
        self.__List_Destroy(pipe.n1.pipes, pipe)
        self.__List_Destroy(pipe.n2.pipes, pipe)


        #path = bresenham.Line(pipe.n1.pos, pipe.n2.pos)
        #for gpos in path:
        #    if ( self.pipe_grid.has_key(gpos) ):
        #        l = self.pipe_grid[ gpos ]
        #        self.__List_Destroy(l, pipe)
        #        if ( len(l) == 0 ):
        #            del self.pipe_grid[ gpos ]

   
    def __List_Destroy(self, lst, itm):
        l = len(lst)
        for i in reversed(xrange(l)):
            if ( lst[ i ] == itm ):
                assert itm == lst.pop(i)

    def Make_Well(self, teaching=False, inhibit_effects=False):
        self.dirty = True
        (mx, my) = GRID_SIZE

        while True:
            x = random.randint(0, mx - 1)
            y = random.randint(0, my - 1)
            if ( teaching ):
                if ( x < cx ):
                    x += cx
            # occupied
            if self.ground_grid.has_key((x,y)):
                continue

            # too close to a city?
            for cx, cy in self.cities_list:
                if math.hypot(x - cx, y - cy) < 10:
                    continue
            # too close to a rock
            if is_too_close((x, y), self.rock_list, 3):
                continue

            w = Well((x,y))
            self.Add_Grid_Item(w, inhibit_effects or teaching)
            return


    def Make_Ready_For_Save(self):
        for p in self.pipe_list:
            p.Make_Ready_For_Save()
            
            
        

