# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 


import pygame , time
from pygame.locals import *

import stats

__messages = []
__day = 0
__change = False

MSG_MAX = 5
MSG_MARGIN = 5
MSG_EXPIRY_TIME = 5

def Has_New_Mail():
    global __messages, __change

    # Limit number of on-screen messages
    while ( len(__messages) > MSG_MAX ):
        __messages.pop(0)
        __change = True

    # Expire old messages
    cur_time = time.time()
    while (( len(__messages) != 0 )
    and ( __messages[ 0 ][ 0 ] <= cur_time )):
        __messages.pop(0)
        __change = True

    x = __change
    __change = False
    return x

def Draw_Mail(output):
    # Purge old messages, one for each run
    if __messages and __messages[0][0] < time.time():
        __messages.pop(0)

    # Show current messages
    y = output.get_rect().height - MSG_MARGIN

    for (tm, surf) in reversed(__messages):
        y -= surf.get_rect().height

        r = surf.get_rect()
        r.topleft = (MSG_MARGIN, y)
        output.blit(surf, r.topleft)


def Set_Day(day):
    global __day
    __day = int(day)

def blur_surf(surface, blur):
    scale = 1.0 / float(blur)
    surf_size = surface.get_size()
    scale_size = (int(surf_size[0] * scale), int(surf_size[1] * scale))
    surf = pygame.transform.smoothscale(surface, scale_size)
    surf = pygame.transform.smoothscale(surf, surf_size)
    return surf

def pretty_text_render(text, colour, background=(0, 0, 0), fsize=20, blur=1.5):
    """Render text with a blurred background color"""
    s = stats.Get_Font(fsize).render(text, True, background)
    s = blur_surf(s, blur)
    for x in xrange(2): # strenghten the shadow
        s.blit(s, (0, 0))
    fg = stats.Get_Font(fsize).render(text, True, colour)
    for x in xrange(2): # strenghten the shadow
        s.blit(fg, (0, 0))
    return s

def New_Mail(text, colour=(255,255,255)):
    global __messages, __day, __change
    text = ( "Day %u: " % __day ) + text
    s = pretty_text_render(text, colour)
    __messages.append((time.time() + MSG_EXPIRY_TIME, s))

    if len(__messages) > MSG_MAX:
        __messages.pop(0)

    __change = True

def Initialise():
    global __messages
    __messages = []
    __change = True



