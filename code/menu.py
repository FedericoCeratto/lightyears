# This Python file uses the following encoding: utf-8
# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

# A very lightweight menu system.

import pygame
from pygame.locals import *
from primitives import *

import stats , extra , resource , render , sound

from logging import getLogger
log = getLogger(__name__)

class Menu(object):
    def __init__(self, menu_options, force_width=0, title=None):
        self._options = menu_options
        self._title = title

        self.control_rects = []
        self.hover = None
        self.bbox = None

        self.selection = None
        self.update_required = True

        width_hint = height_hint = 10

        if force_width > 0:
            width_hint = force_width

        # Two attempts at drawing required.
        (discard1, discard2,
            (width_hint, height_hint)) = self._draw((width_hint, height_hint))

        if width_hint < 150:
            width_hint = 150
        if force_width > 0:
            width_hint = force_width

        (self.surf_store, self.control_rects,
            (discard1, discard2)) = self._draw((width_hint, height_hint))

        self.bbox = Rect(0, 0, width_hint, height_hint)

    def Get_Command(self):
        return self.selection

    def Select(self, snum):
        self.update_required = True
        self.selection = snum

    def Mouse_Move(self, spos):
        if (( spos is None )
        or ( not self.bbox.collidepoint(spos) )):
            self.hover = None
            return

        self.update_required = True
        (x,y) = spos

        old_sel = self.hover
        self.hover = None
        x -= self.bbox.left
        y -= self.bbox.top
        for (num, r) in self.control_rects:
            if r.collidepoint(x,y):
                self.hover = num
                if old_sel != self.hover:
                    sound.FX("click_s")
                return

    def Mouse_Down(self, spos):

        self.Mouse_Move(spos)
        if self.hover is not None:
            self.selection = self.hover
            sound.FX("click")

    def Key_Press(self, k):
        """Handle key press on general menu."""
        for (num, name, hotkeys) in self._options:
            if hotkeys is not None and k in hotkeys:
                self.selection = num
                self.update_required = True
                sound.FX("click")
                return

    def Draw(self, output, centre=None, top=None):
        if self.update_required:
            self.update_required = False

            if centre is not None:
                self.bbox.center = centre
            elif top is not None:
                # in-game menu
                self.bbox.top = top
            else:
                # centered menu
                self.bbox.center = output.get_rect().center

            self.bbox.clamp_ip(output.get_rect())

            output.blit(self.surf_store, self.bbox.topleft)

            for (num, r) in self.control_rects:
                r = Rect(r)
                r.top += self.bbox.top
                r.left += self.bbox.left
                if num == self.selection:
                    pygame.draw.rect(output, (255, 255, 255), r, 1)
                elif num == self.hover:
                    if self.hover == Menu.title:
                        pass # titles do not hover
                    else:
                        pygame.draw.rect(output, (0, 180, 0), r, 1)


    def _draw(self, (width_hint, height_hint)):
        surf = pygame.Surface((width_hint, height_hint))
        bbox = Rect(0, 0, width_hint, height_hint)

        extra.Tile_Texture(surf, "006metal.jpg", surf.get_rect())

        margin = 8
        w = bbox.width - ( margin * 2 )
        th = None
        y = margin + bbox.top
        control_rects = []
        max_width = 0
        first_item = True

        for (num, name, hotkeys) in self._options:
            if name is None: # a gap
                if first_item:
                    img = resource.Load_Image("header.jpg")
                    img_r = img.get_rect()
                    img_r.center = bbox.center
                    img_r.top = y
                    surf.blit(img, img_r.topleft)
                    extra.Edge_Effect(surf, img_r)
                    max_width = img_r.width + ( margin * 2 )
                    y += img_r.height

                y += margin * 2
                continue

            txt = render.Render(name, 18, (50,200,20), (200,200,0))
            if th is None:
                th = txt.get_rect().height + ( margin * 2 )
            tw = txt.get_rect().width + ( margin * 2 )
            if tw > max_width:
                max_width = tw

            x = bbox.left + margin 
            r = Rect(x,y,w,th)
            x += self.Justify(w,txt.get_rect().width)
        
            extra.Tile_Texture(surf, "greenrust.jpg", r)
            extra.Edge_Effect(surf, r)
            self.Enhancement_Interface(surf, num, r, margin)

            surf.blit(txt, (x,y + margin - 1))
            y += th + margin
            control_rects.append((num, r))

            first_item = False


        # Finalise drawing
        extra.Line_Edging(surf, bbox, True)

        return (surf, control_rects, (max_width, y))


    def Justify(self, width, text_width):
        return ( width - text_width ) / 2

    def Enhancement_Interface(self, surf, num, rect, margin):
        pass

    # Menu type enum. Each variable is an attribute, e.g. Menu.load = 1
    save, load, hide, quit, fullscreen, tutorial, new_game, res, menu, review, \
    beginner, intermediate, expert, prev, next, updates, website, manual, \
    mute, peaceful, multiplayer_game, title, input_field, input_submit, \
    input_cancel, multiplayer_server_name, multiplayer_player_name, \
    multiplayer_new_game_name, multiplayer_join_game, title, lbox_up, lbox_dn, \
    game_1, game_2, game_3, game_4, game_5 = range(37)


class InputMenu(Menu):
    """Input Menu"""
    def __init__(self, title, current_value):
        self.value = current_value
        self._tmp_value = self.value
        self.is_focused = False
        if current_value is None:
            current_value = '[empty]'
        menu_options = [
            (Menu.title, title, []),
            [Menu.input_field, current_value, []],
            (Menu.input_submit, "Submit", []),
            (Menu.input_cancel, "Cancel", []),
        ]
        Menu.__init__(self, menu_options, 0)

    def submit(self):
        self.value = self._tmp_value

    def set_focus_on_input(self):
        self.is_focused = True

    def Key_Press(self, k):
        if self.hover == Menu.input_field:
            if self._tmp_value in (None, '[empty]'):
                self._tmp_value = ''

            if k in xrange(33, 126):
                self._tmp_value += chr(k)
                print self._tmp_value
            elif k == 8:
                self._tmp_value = self._tmp_value[:-1]
                print self._tmp_value
            else:
                return

            self._options[1][1] = self._tmp_value
            self.update_required = True
            width_hint = height_hint = 10

            # Two attempts at drawing required.
            (discard1, discard2,
                (width_hint, height_hint)) = self._draw((width_hint, height_hint))

            if width_hint < 150:
                width_hint = 150
            (self.surf_store, self.control_rects,
                (discard1, discard2)) = self._draw((width_hint, height_hint))


class GamesListMenu(Menu):
    """Input Menu"""
    def __init__(self):
        self.selected_game = None
        self._scroll_pos = 0
        self._ndg = 5 # Number of displayed games
        self._displayed_game_names = [(x, '[empty]') for x in xrange(self._ndg)]
        self._options = self._build_menu_options()
        Menu.__init__(self, self._options, 0)

    def update_games_list(self, game_names):
        """Update existing games list"""
        self._game_names = sorted(game_names)
        self._update_screen()

    def scroll_up(self):
        if self._scroll_pos:
            self._scroll_pos -= 1
            self._update_screen()

    def scroll_down(self):
        if self._scroll_pos < len(self._game_names) / self._ndg:
            self._scroll_pos += 1
            self._update_screen()

    def get_game_name(self, n):
        """Get a game name based on the displayed ones"""
        n -= Menu.game_1
        return dict(self._displayed_game_names)[n]

    def _build_menu_options(self):
        games_list = [(n + Menu.game_1, gn, [])
            for n, gn in self._displayed_game_names]

        top = [
            (Menu.title, "Multiplayer games", []),
            (None, None, []),
            (Menu.lbox_up, u'▲', []),
        ]

        bottom = [
            (Menu.lbox_dn, u'▼', []),
            (None, None, []),
            (Menu.input_cancel, "Cancel", []),
        ]
        return top + games_list + bottom

    def _update_screen(self):
        """Rebuild menu items and update screen"""
        start = self._scroll_pos * self._ndg
        end = (self._scroll_pos + 1) * self._ndg
        self._displayed_game_names = list(
            enumerate(self._game_names[start:end]))
        self._options = self._build_menu_options()

        width_hint = height_hint = 10

        # Two attempts at drawing required.
        (discard1, discard2,
            (width_hint, height_hint)) = self._draw((width_hint, height_hint))

        if width_hint < 150:
            width_hint = 150
        (self.surf_store, self.control_rects,
            (discard1, discard2)) = self._draw((width_hint, height_hint))


class OOMenu(Menu):
    def __init__(self):
        Menu.__init__(self, [], 0)

class Input(object):
    """One-field input box"""
    def __init__(self, title, current_value=''):
        self._title = title
        self._current_value = current_value

    def on_change(self):
        """Redefine this method to execute actions on value change"""
        raise NotImplementedError


class ListBox(object):
    def __init__(self, title, current_value=''):
        self._title = title
        self._current_value = current_value

    def on_change(self):
        """Redefine this method to execute actions on value change"""
        raise NotImplementedError

class Btn(object):
    def __init__(self, title, hotkey=''):
        self._title = title

    def on_click(self):
        """Redefine this method to execute actions on click"""
        raise NotImplementedError

class MultiplayerMenu(Menu):
    def __init__(self):
        self._title = 'Multiplayer'
        self.server_name = Input('Server name')
        self.new_game_name = Input('Create new game')
        self.games_list = Games
        self._items = (self.server_name, self.new_game_name, self.games_list)


