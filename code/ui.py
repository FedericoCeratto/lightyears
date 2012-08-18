# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

# Do you believe in the users?

import pygame , random
from pygame.locals import *

import stats , menu , draw_obj , mail , particle , tutor
import resource
from map_items import *
from primitives import *

from mail import New_Mail
from multiplayer import UserException

import logging
log = logging.getLogger(__name__)

class Gauge(object):
    """Round steampunk gauge"""
    def __init__(self, x, y, d):
        d = d * Get_Grid_Size() # diameter
        self.back_img = resource.Load_Image("gauge.png", scale_to=(d, d))
        self.hand_img = resource.Load_Image("gauge_hand.png", scale_to=(d, d))
        self.glass_img = resource.Load_Image("gauge_glass.png", scale_to=(d, d))
        self._pos = GVector(x, y).in_pixels
        self._animated_pressure = 0
        self._speed = .2
        self._vibration = random.randint(0, 200)

    def rotate_hand(self, bar=None):
        """Rotate pressure hand"""
        if bar is None:
            bar = 0
        angle = 199 - bar / 27.0 * 170
        center = self.hand_img.get_rect().center
        hand = pygame.transform.rotate(self.hand_img, angle)
        newrect = hand.get_rect()
        newrect.center = center
        return hand, newrect

    def draw(self, output, bar=None):
        """Draw gauge and hand"""
        # the pressure displayed by the gauge will reach "bar" eventually
        delta = (bar - self._animated_pressure) * self._speed
        self._animated_pressure += delta

        bar = self._animated_pressure

        # animate vibration
        v = self._vibration
        if v > 200:
            self._vibration = 0
        if v % 2 == 0:
            if v < 40:
                bar += v / 100.0
            elif v < 80:
                bar += (80 - v) / 100.0
        self._vibration += 1

        hand, hand_rect = self.rotate_hand(bar=bar)

        output.blit(self.back_img, self._pos)
        output.blit(hand, self._pos + hand_rect)
        output.blit(self.glass_img, self._pos)

class Valve(object):
    """Big valve"""
    def __init__(self):
        self._pos = PVector(9.5 * Get_Grid_Size(), 0)
        h = 5 * Get_Grid_Size() # height
        d = Get_Grid_Size() # handle diameter

        self._back_img = resource.Load_Image("valve_back.png", scale_to=(None, h))
        self._handle_img = resource.Load_Image("valve_handle.png", scale_to=(d, d))
        self._anim_rotation = self._gen_animate_rotation()
        self._anim_rotation.next()

    def _gen_animate_rotation(self):
        """Generate handle rotation animation"""
        angle = 0
        is_open = True
        while True:
            if angle < 30 and not is_open:
                angle += 4
            elif angle > 0 and is_open:
                angle -= 4
            is_open = (yield angle)

    def rotate_handle(self, is_open):
        """Rotate handle"""
        if is_open is None:
            angle = 0 # no pipe selected
        else:
            angle = self._anim_rotation.send(is_open)

        center = self._handle_img.get_rect().center
        handle = pygame.transform.rotate(self._handle_img, angle)
        newrect = handle.get_rect()
        newrect.center = GVector(-.55, 1.38).in_pixels + PVector(center)
        return handle, newrect

    def draw(self, output, is_open=None):
        output.blit(self._back_img, self._pos)
        if is_open is not None:
            handle, handle_rect = self.rotate_handle(is_open=is_open)
            output.blit(handle, self._pos + handle_rect)

class User_Interface:
    def __init__(self, net, (width, height), g):
        self.net = net
        self.control_menu = None
        self._game_data = g

        self.Reset()
        self.blink = 0xff

        # Although there is only one base image, it is scaled and
        # cropped on startup to create different backdrops.
        # (Note: These don't get saved, as they're part of the UI. That's bad.)

        img = resource.Load_Image("moon_surface.jpg")
        zoom = 1 + random.random() # zoom in between 1 and 2
        scaled = pygame.transform.smoothscale(img,
            (int(width * zoom), int(height * zoom))
        )

        # get random coordinates to extract a background surface
        x = randint(0, scaled.get_width() - width)
        y = randint(0, scaled.get_height() - height)
        self.background = pygame.Surface((width, height),flags=pygame.SRCALPHA)
        self.background.blit(scaled, (0,0),(x, y, x + width, y + height))


        self.steam_effect = particle.Make_Particle_Effect(particle.Steam_Particle)
        self.steam_effect_frame = 0

        self.gauges = dict(
            city_pressure = Gauge(0, 0, 4),
            selected_pressure = Gauge(4.5, 0, 4)
        )
        self.valve = Valve()

        self.vehicle_list = []
        #self.vehicle_list.extend(
        #    Transport(network=self.net) for x in xrange(2)
        #)
        #self.vehicle_list.extend(
        #    [Tank(network=self.net, vehicles=self.vehicle_list) for x in xrange(10)]
        #)

    def Update_Area(self, area):
        if ( area != None ):
            self.partial_update = True

            # pygame.Rect is rather good.

            if ( len(self.update_area_list) == 0 ):
                self.update_area_list = [area]
            else:
                ci = area.collidelist(self.update_area_list)
                if ( ci < 0 ):
                    # New area!
                    self.update_area_list.append(area)
                else:
                    # Area overlaps an existing area, which gets expanded.
                    self.update_area_list[ ci ].union_ip(area)

    def Draw_Game(self, output, season_fx):
        blink = self.blink

        if ( season_fx.Is_Shaking() and not self.Is_Menu_Open() ):
            # Earthquake effect
            m = 6
            r = output.get_rect()
            r.left += random.randint(-m, m)
            r.top += random.randint(-m, m)
            r = output.get_rect().clip(r)
            output = output.subsurface(r)

        if ( self.net.dirty ):
            self.net.dirty = False

        output.blit(self.background,(0,0))

        self.__Update_Reset()

        for w in self.net.well_list:
            w.Draw(output)
            self.Add_Steam_Effect(output, w.pos)

        if ( self.selection != None ):
            # highlight selection
            r = self.selection.Draw_Selected(output, (blink, blink, 0))
            self.Update_Area(r)

        for p in self.net.pipe_list:
            p.Draw(output)

        for n in self.net.node_list:
            n.Draw(output)
            if ( n.emits_steam ):
                self.Add_Steam_Effect(output, n.pos)

        for r in self.net.rock_list:
            r.Draw(output)

        for v in self.vehicle_list:
            v.draw(output)

        season_fx.Draw(output, self.Update_Area)


        gpos = self.mouse_pos
        if ( gpos != None ):
            if ( self.mode == BUILD_NODE ):
                # could put a node here.
                r = Grid_To_Scr_Rect(gpos)
                self.Update_Area(r)
                # In multiplayer mode, nodes can be placed only in proximity
                # of owned nodes
                if self._game_data.multiplayer and \
                    not self.net.is_closed_to_an_owned_node(gpos):
                    color = (255, 0, 0, 200)
                else:
                    color = (255, 255, 0, 200)

                draw_ellipse(output, Point(r.topleft), 1, color, 1)
                # draw excavation shadow
                draw_ellipse(output, Point(r.topleft),
                    INITIAL_NODE_EXCAVATION_DISTANCE, (0, 0, 0, 10), 1,
                    filled=True)
                # draw excavation limit
                draw_ellipse(output, Point(r.topleft),
                    INITIAL_NODE_EXCAVATION_DISTANCE , (0, 0, 0, 30), 1)

            elif (( self.mode == BUILD_PIPE )
            and ( self.selection != None )
            and ( isinstance(self.selection, Node) )):
                # pipe route illustrated

                sp = Grid_To_Scr(self.selection.pos)
                ep = Grid_To_Scr(gpos)
                colour = (80,80,50)

                if ( not self.net.Pipe_Possible(self.selection.pos, gpos) ):
                    colour = (100,0,0)

                r = Rect(sp,(2,2)).union(Rect(ep,(2,2)))
                self.Update_Area(r)

                pygame.draw.line(output, colour, sp, ep, 2)
    
        for item in self.net.popups:
            r = item.Draw_Popup(output)
            self.Update_Area(r)

        mail.Draw_Mail(output)

        if ( not self.Is_Menu_Open () ):
            self.blink = 0x80 | ( 0xff & ( self.blink + 0x10 ))
            self.steam_effect_frame = ( 
                self.steam_effect_frame + 1 ) % len(self.steam_effect)

        if ( DEBUG_GRID ):
            self.Debug_Grid(output)

    def Draw_Selection(self, output):
        output.fill((20,0,0))
        if ( self.selection != None ):
            r = output.get_rect()
            r.center = Grid_To_Scr(self.selection.pos)

            for p in self.net.pipe_list:
                p.Draw_Mini(output, r.topleft)

            for n in self.net.node_list:
                n.Draw_Mini(output, r.topleft)

    def Draw_Stats(self, output, default_stats):
        if ( self.selection == None ):
            l = default_stats
        else:
            l = self.selection.Get_Information()
            if ( not self.net.Is_Connected(self.selection) ):
                l += [ ((255,0,0), 15, "Not connected to network") ]

        h = hash(str(l))
        if ( h != self.stats_hash ):
            # Stats have changed.
            output.fill((0,0,0))
            stats.Draw_Stats_Window(output, l)
            self.stats_hash = h

        
    def Draw_Controls(self, output):
        if ( self.control_menu == None ):
            self.__Make_Control_Menu(output.get_rect().width)

        # draw city pressure gauge
        self.gauges['city_pressure'].draw(
            output,
            bar=self.net.hub.Get_Pressure() * .4,
        )

        # draw selected item gauge
        if isinstance(self.selection, Node):
            bar = self.selection.steam.Get_Pressure() * .4
        elif isinstance(self.selection, Pipe):
            bar = self.selection.current_n1_to_n2
            bar = abs(bar)
        else:
            bar = 0
        self.gauges['selected_pressure'].draw(
            output,
            bar=bar,
        )

        if isinstance(self.selection, Pipe):
            self.valve.draw(output, is_open=self.selection.valve_open)
        else:
            self.valve.draw(output)

        self.control_menu.Draw(output, top=5*Get_Grid_Size())

    def Control_Mouse_Move(self, spos):
        if ( self.control_menu != None ):
            self.control_menu.Mouse_Move(spos)

    def Control_Mouse_Down(self, spos):
        if ( self.control_menu != None ):
            self.control_menu.Mouse_Down(spos)
            self.mode = self.control_menu.Get_Command()

            if ( self.selection != None ):
                if ( self.mode == DESTROY ):
                    self.net.Destroy(self.selection)
                    self.__Clear_Control_Selection()
                    self.selection = None

                elif ( self.mode == UPGRADE ):
                    self.selection.Begin_Upgrade()
                    self.__Clear_Control_Selection()

    def Key_Press(self, k):
        if ( self.control_menu != None ):
            self.control_menu.Key_Press(k)
            self.mode = self.control_menu.Get_Command()

    def Right_Mouse_Down(self):
        self.selection = None
        self.mouse_pos = None
        self.__Clear_Control_Selection()

    def __Clear_Control_Selection(self):
        self.mode = NEUTRAL
        if ( self.control_menu != None ):
            self.control_menu.Select(NEUTRAL)

    def Reset(self):
        self.selection = None
        self.mouse_pos = None
        self.__Clear_Control_Selection()
        self.stats_hash = 0
        self.__Update_Reset()

    def __Update_Reset(self):
        self.partial_update = False
        self.update_area_list = []

    def Is_Menu_Open(self):
        return ( self.mode == OPEN_MENU )

    def _build_node(self, gpos, tutor):
        """Create new node if possible"""
        if not self.net.metal_available('node'):
            return

        n = Node(gpos, rocks=self.net.rock_list)

        # In multiplayer mode, nodes can be placed only in proximity
        # of owned nodes
        if self._game_data.multiplayer:
            if not self.net.is_closed_to_an_owned_node(gpos):
                New_Mail("This location is too far from your network.")
                return

            try:
                self._game_data.multiplayer.add_node(gpos)
            except UserException, e:
                log.error("Not building node: %s" % e)
                return

        self.net.use_metal('node')
        n.Sound_Effect()
        self.selection = None
        if self.net.Add_Grid_Item(n):
            self.selection = n
            tutor.Notify_Add_Node(n)

    def _build_node_on_well(self, gpos, tutor):
        """Create new well node if possible"""
        if not self.net.metal_available('node'):
            return

        n = Well_Node(gpos)

        if self._game_data.multiplayer:
            try:
                self._game_data.multiplayer.add_well_node(gpos)
            except UserException, e:
                log.debug("Not building well node: %s" % e)
                return

        self.net.use_metal('well')
        n.Sound_Effect()
        if self.net.Add_Grid_Item(n):
            self.selection = n
            tutor.Notify_Add_Node(n)

    def _build_pipe(self, start, end, tutor):
        """Build new pipe if possible"""
        # In multiplayer mode, pipes can be built only between
        # owned nodes
        if self._game_data.multiplayer:
            if (start.owned_by_me and end.owned_by_me):
                # Player owns both nodes
                self._game_data.multiplayer.add_pipe(
                    (start.pos, end.pos))
            elif (start.owned_by_me and end.is_connectable) or \
                (start.is_connectable and end.owned_by_me):
                # Player owns one node, the other is not connected to anything else
                self._game_data.multiplayer.add_pipe(
                    (start.pos, end.pos))
            else:
                New_Mail("Endpoint not in your network.")
                return

        if self.net.Add_Pipe(start, end):
            tutor.Notify_Add_Pipe()
            self.selection = None

    def Game_Mouse_Down(self, spos):
        gpos = Scr_To_Grid(spos)

        if (( self.selection != None )
        and ( self.selection.Is_Destroyed() )):
            self.selection = None

        if ( DEBUG ):
            print 'Selection:',self.selection
            for (i,n) in enumerate(self.net.node_list):
                if ( n == self.selection ):
                    print 'Found: node',i
            for (i,p) in enumerate(self.net.pipe_list):
                if ( p == self.selection ):
                    print 'Found: pipe',i
            print 'End'


        if ( not self.net.ground_grid.has_key(gpos) ):
            self.selection = self.net.Get_Pipe(gpos)

            # empty (may contain pipes)
            if ( self.mode == BUILD_NODE ):
                # create new node
                self._build_node(gpos, tutor)

            elif ( self.mode == DESTROY ):
                # I presume you are referring to a pipe?
                pipe = self.selection
                if ( pipe != None ):
                    self.net.Destroy(pipe)
                    self.__Clear_Control_Selection()
                self.selection = None

            elif ( self.mode == UPGRADE ):
                if ( self.selection != None ):

                    if self.net.use_metal('up_node'):
                        self.selection.Begin_Upgrade()
                        self.__Clear_Control_Selection()

            elif ( self.selection != None ):
                self.selection.Sound_Effect()
                
        elif ( isinstance(self.net.ground_grid[ gpos ], Node)):
            # Contains node

            n = self.net.ground_grid[ gpos ]
            if ( self.mode == BUILD_PIPE ):
                if (( self.selection == None )
                or ( isinstance(self.selection, Pipe))):
                    # start a new pipe here
                    self.selection = n
                    n.Sound_Effect()

                elif (( isinstance(n, Node) )
                and ( isinstance(self.selection, Node) )
                and ( n != self.selection )):
                    # end pipe here
                    self._build_pipe(self.selection, n, tutor)

            elif ( self.mode == DESTROY ):
                self.net.Destroy(n)
                self.selection = None
                self.__Clear_Control_Selection()

            elif ( self.mode == UPGRADE ):
                if self.net.use_metal('up_node'):
                    n.Begin_Upgrade()
                self.selection = n
                self.__Clear_Control_Selection()

            else:
                self.selection = n
                n.Sound_Effect()

        elif ( isinstance(self.net.ground_grid[ gpos ], Well)):
            # Contains well (unimproved)
            w = self.net.ground_grid[ gpos ]
            if ( self.mode == BUILD_NODE ):
                # A node is planned on top of the well.
                self._build_node_on_well(gpos, tutor)

        ## Select a rock
        #for rock in self.net.rock_list:
        #    if rock.pos == gpos:
        #        self.selection = rock
        #        rock.Sound_Effect()
        #        continue

        self.net.Popup(self.selection)
        tutor.Notify_Select(self.selection)

    def Game_Mouse_Move(self, spos):
        self.mouse_pos = Scr_To_Grid(spos)
        if ( self.control_menu != None ):
            self.control_menu.Mouse_Move(None)

    def Debug_Grid(self, output):
        (mx, my) = GRID_SIZE
        for y in xrange(my):
            for x in xrange(mx):
                if ( self.net.pipe_grid.has_key( (x,y) ) ):
                    r = Grid_To_Scr_Rect((x,y))
                    pygame.draw.rect(output, (55,55,55), r, 1)
                    r.width = len(self.net.pipe_grid[ (x,y) ]) + 1
                    pygame.draw.rect(output, (255,0,0), r)

    def Add_Steam_Effect(self, output, pos):
        sfx = self.steam_effect[ self.steam_effect_frame ]
        r = sfx.get_rect()
        r.midbottom = Grid_To_Scr(pos)
        output.blit(sfx, r.topleft)
        self.Update_Area(r)

    def __Make_Control_Menu(self, width):
        pictures = dict()
        pictures[ BUILD_NODE ] = "bricks.png"
        pictures[ BUILD_PIPE ] = "bricks2.png"
        pictures[ DESTROY ] = "destroy.png"
        pictures[ UPGRADE ] = "upgrade.png"
        pictures[ OPEN_MENU ] = "menuicon.png"

        self.control_menu = menu.Enhanced_Menu([
                (BUILD_NODE, "Build &Node", [ K_n ]),
                (BUILD_PIPE, "Build &Pipe", [ K_p ]),
                (DESTROY, "&Destroy", [ K_d , K_BACKSPACE ]),
                (UPGRADE, "&Upgrade", [ K_u ]),
                (None, None, None),
                (OPEN_MENU, "Menu", [ K_ESCAPE ])], 
                pictures, width)

    def Frame_Advance(self, frame_time):
        for p in self.net.pipe_list:
            p.Frame_Advance(frame_time)


