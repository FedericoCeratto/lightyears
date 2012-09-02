# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 

from argparse import ArgumentParser
import pygame , random , sys , math , time , webbrowser , urllib , os
from pygame.locals import *
from getpass import getuser

import game , stats , storms , extra , save_menu , resource , menu
import config , startup , sound , alien_invasion , quakes
from primitives import *
from multiplayer import Reactor

DEB_ICON = '/usr/share/pixmaps/lightyears.xpm'
DEB_MANUAL = '/usr/share/doc/lightyears/html/index.html'

import logging
log = logging.getLogger(__name__)

def setup_logging():
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

def parse_args():
    """Parse CLI options
    :returns: args
    """
    p = ArgumentParser()
    p.add_argument("-f", "--fullscreen",
        help="fullscreen", action="store_true")
    p.add_argument("--safe",
        help="safe mode", action="store_true")
    p.add_argument("--no-sound",
        help="disable sound", action="store_true")
    p.add_argument("-m", "--multiplayer",
        help="start multiplayer game using server:game:player names", 
        dest='multiplayer_parameters')
    for t in ('beginner', 'intermediate', 'expert', 'peaceful'):
        p.add_argument("--play-%s" % t,
            help="start %s game" % t, action="store_true")

    x_res_li = [r[0] for r in RESOLUTIONS]
    x_res = ', '.join(map(str, x_res_li))
    p.add_argument("--resolution", type=int,
        help="resolution (one of: %s)" % x_res)
    args = p.parse_args()

    if args.multiplayer_parameters:
        # Only peaceful mode is supported in multiplayer
        args.play_peaceful = True
        args.play_beginner = False
        args.play_intermediate = False
        args.play_expert = False

    if args.resolution is None:
        return args

    for w, h, fs in RESOLUTIONS:
        if args.resolution == w:
            args.resolution = (w, h)
            return args

    print "Incorrect resolution specified."
    sys.exit(1)

def Main(data_dir):

    n = "20,000 Light-Years Into Space"
    print ""
    print n
    print "Copyright (C) Jack Whitham 2006-11"
    print "Version", config.CFG_VERSION
    print ""

    setup_logging()
    cli_args = parse_args()

    resource.DATA_DIR = data_dir

    config.Initialise(cli_args.safe)

    # Pygame things
    flags = 0
    if cli_args.fullscreen:
        flags |= FULLSCREEN

    bufsize = 2048

    if not cli_args.no_sound:
        try:
            pygame.mixer.pre_init(22050, -16, 2, bufsize)
            pygame.mixer.init()
        except pygame.error, message:
            print 'Sound initialization failed. %s' % message
            cli_args.no_sound = True

    pygame.init()
    pygame.font.init()

    if flags & FULLSCREEN:
        # Ensure that all resolutions are supported by the system
        for resolution in RESOLUTIONS:
            if resolution[:2] not in pygame.display.list_modes():
                RESOLUTIONS.remove(resolution)

        
    if cli_args.no_sound:
        resource.No_Sound()
    else:
        pygame.mixer.init(22050,-16,2,bufsize)

    if cli_args.resolution is None:
        resolution = config.cfg.resolution
    else:
        resolution = cli_args.resolution

    clock = pygame.time.Clock()
    screen = pygame.display.set_mode(resolution, flags)
    height = screen.get_rect().height
    width = screen.get_rect().width

    # Icon
    # The icon provided in the Debian package is different than the original one
    # (size and location changed)
    if os.path.isfile(DEB_ICON):
        pygame.display.set_icon(resource.Load_Image(DEB_ICON))
    else:
        pygame.display.set_icon(resource.Load_Image("32.png"))

    # Game begins.. show loading image
    screen.fill((0,0,0))
    pygame.display.flip()
    pygame.display.set_caption(n)
    storms.Init_Storms()
    alien_invasion.Init_Aliens()
    quakes.Init_Quakes()

    quit = False
    while ( not quit ):
        if resolution != (width, height):

            # As the toggle mode thing doesn't work outside of Unix, 
            # the fallback strategy is to do set_mode again.
            # But if you set the same mode, then nothing happens.
            # So:
            screen = pygame.display.set_mode((640,480), flags)  # not the right mode
            screen = pygame.display.set_mode(resolution, flags) # right mode!
            height = screen.get_rect().height
            width = screen.get_rect().width

        quit = Main_Menu_Loop(n, clock, screen, (width, height), cli_args)

    config.Save()

    # Bye bye Pygame.
    pygame.mixer.quit()
    pygame.quit()


def Main_Menu_Loop(name, clock, screen, (width, height), cli_args):
    # Further initialisation
    menu_image = resource.Load_Image("mainmenu.jpg")

    if ( menu_image.get_rect().width != width ):
        menu_image = pygame.transform.scale(menu_image, (width, height))

    stats.Set_Font_Scale(config.cfg.font_scale)

    main_menu = current_menu = menu.Menu([ 
                (None, None, []),
                (MENU_TUTORIAL, "Play Tutorial", []),
                (MENU_NEW_GAME, "Play New Game", []),
                (MENU_MULTIPLAYER_GAME, "Play Multiplayer Game", []),
                (MENU_LOAD, "Restore Game", []),
                (None, None, []),
                (MENU_RES, "Set Graphics Resolution", []),
                (MENU_MUTE, "Toggle Sound", []),
                (MENU_MANUAL, "View Manual", []),
                (MENU_UPDATES, "Check for Updates", []),
                (None, None, []),
                (MENU_QUIT, "Exit to " + extra.Get_OS(), 
                    [ K_ESCAPE , K_F10 ])],
                title = 'Main menu',
    )
    resolution_menu = menu.Menu( 
                [(None, None, [])] + [
                (w, "%u x %u" % (w,h), [])
                    for (w, h, fs) in RESOLUTIONS ] +
                [(None, None, []),
                (-1, "Cancel", [])])
    difficulty_menu = menu.Menu(
                [(None, None, []),
                (MENU_TUTORIAL, "Tutorial", []),
                (None, None, []),
                (MENU_BEGINNER, "Beginner", []),
                (MENU_INTERMEDIATE, "Intermediate", []),
                (MENU_EXPERT, "Expert", []),
                (None, None, []),
                (MENU_PEACEFUL, "Peaceful", []),
                (None, None, []),
                (-1, "Cancel", [])])

    new_multiplayer_menu = menu.Menu(
                [(None, None, []),
                (MENU_MULTIPLAYER_SERVER_NAME, "Set server", []),
                (MENU_MULTIPLAYER_PLAYER_NAME, "Set player name", []),
                (MENU_MULTIPLAYER_NEW_GAME_NAME, "Create new game", []),
                (MENU_MULTIPLAYER_JOIN_GAME, "Join", []),
                (None, None, []),
                (-1, "Cancel", [])],
                title = 'Multiplayer',
    )

    multiplayer_games_menu = menu.GamesListMenu()

    multiplayer_server_name_input = menu.InputMenu('Server name', 'localhost')
    multiplayer_game_name_input = menu.InputMenu('Game name', 'newgame')
    multiplayer_player_name_input = menu.InputMenu('Player name', getuser())

    copyright = [ name,
            "Copyright (C) Jack Whitham 2006-11 - website: www.jwhitham.org",
            None,
            "Game version " + config.CFG_VERSION ]


    if cli_args.multiplayer_parameters:
        # Start Multiplayer game from CLI
        try:
            server_name, game_name, player_name = \
                cli_args.multiplayer_parameters.split(':')
        except ValueError:
            print "Incorrect multiplayer parameter format"
            sys.exit(1)

        multiplayer_server_name_input.value = server_name
        multiplayer_game_name_input.value = game_name
        multiplayer_player_name_input.value = player_name

        mreactor = Reactor(
            multiplayer_server_name_input.value,
            multiplayer_player_name_input.value,
        )
        mreactor.create_game(multiplayer_game_name_input.value)
        res = mreactor.join_game(game_name)
        quit = game.Main_Loop(screen, clock,
             (width,height), None, MENU_PEACEFUL, mreactor=mreactor)
        game.multiplayer = mreactor


    # --play-<gametype> or --multiplayer starts a game immediately
    flags = (
        #('multiplayer_parameters', MENU_MULTIPLAYER_JOIN_GAME),
        ('play_beginner', MENU_BEGINNER),
        ('play_intermediate', MENU_INTERMEDIATE),
        ('play_expert', MENU_EXPERT),
        ('play_peaceful', MENU_PEACEFUL),
    )
    for flag, pick_cmd in flags:
        if getattr(cli_args, flag):
            # Multiplayer is supported only here
            #FIXME
            #quit = game.Main_Loop(screen, clock,
            #    (width,height), None, pick_cmd, multiplayer=cli_args.server)
            quit = game.Main_Loop(screen, clock,
                (width,height), None, pick_cmd)

    mreactor = None # Multiplayer reactor

    # off we go.

    quit = False
    while ( not quit ):
        # Main menu
        screen.fill((0,0,0))
        screen.blit(menu_image, (0,0))
      
        y = 5
        sz = 11
        for text in copyright:
            if ( text == None ):
                sz = 7
                continue
            img = stats.Get_Font(sz).render(text, True, (200, 200, 128))
            img_r = img.get_rect()
            img_r.center = (( width * 3 ) / 4, 0)
            img_r.clamp_ip(screen.get_rect())
            img_r.top = y
            screen.blit(img, img_r.topleft)
            y += img_r.height

        (quit, cmd) = extra.Simple_Menu_Loop(screen, current_menu,
                (( width * 3 ) / 4, 10 + ( height / 2 )))

        if ( current_menu == main_menu ):
            if ( cmd == MENU_NEW_GAME ):
                current_menu = difficulty_menu

            if ( cmd == MENU_MULTIPLAYER_GAME ):
                current_menu = new_multiplayer_menu

            elif ( cmd == MENU_TUTORIAL ):
                quit = game.Main_Loop(screen, clock, 
                        (width,height), None, MENU_TUTORIAL)

            elif ( cmd == MENU_LOAD ):
                current_menu = save_menu.Save_Menu(False)

            elif ( cmd == MENU_QUIT ):
                quit = True

            elif ( cmd == MENU_MUTE ):
                config.cfg.mute = not config.cfg.mute
                return False # update menu

            elif ( cmd == MENU_RES ):
                current_menu = resolution_menu

            elif ( cmd == MENU_UPDATES ):
                if Update_Feature(screen, menu_image):
                    url = ( CGISCRIPT + "v=" +
                            startup.Get_Game_Version() )

                    pygame.display.iconify()
                    try:
                        webbrowser.open(url, True, True)
                    except:
                        pass

            elif ( cmd == MENU_MANUAL ):
                pygame.display.iconify()
                if os.path.isfile(DEB_MANUAL):
                    # Debian manual present
                    url = 'file://' + DEB_MANUAL
                else:
                    base = os.path.abspath(resource.Path(os.path.join("..", 
                            "manual", "index.html")))
                    if os.path.isfile(base):
                        # Upstream package manual present
                        url = 'file://' + base
                    else:
                        # No manual? Redirect to website.
                        url = 'http://www.jwhitham.org/20kly/'

                try:
                    webbrowser.open(url, True, True)
                except:
                    pass
                
                
        elif ( cmd != None ):
            if ( current_menu == resolution_menu ):
                for (w, h, fs) in RESOLUTIONS:
                    if ( w == cmd ):
                        config.cfg.resolution = (w, h)
                        resolution = config.cfg.resolution
                        config.cfg.font_scale = fs
                        # change res - don't quit
                        return False

            elif ( current_menu == difficulty_menu ):
                if ( cmd >= 0 ):
                    quit = game.Main_Loop(screen, clock, 
                            (width,height), None, cmd)

            # Global multiplayer menu
            elif current_menu == new_multiplayer_menu:
                if cmd == MENU_MULTIPLAYER_SERVER_NAME:
                    current_menu = multiplayer_server_name_input
                    continue
                elif cmd == MENU_MULTIPLAYER_PLAYER_NAME:
                    current_menu = multiplayer_player_name_input
                    continue
                elif cmd == MENU_MULTIPLAYER_NEW_GAME_NAME:
                    current_menu = multiplayer_game_name_input
                    continue
                elif cmd == MENU_MULTIPLAYER_JOIN_GAME:
                    # Connect to server, list games
                    if mreactor is None:
                        mreactor = Reactor(
                            multiplayer_server_name_input.value,
                            multiplayer_player_name_input.value,
                        )
                    games = mreactor.list_games()
                    multiplayer_games_menu.update_games_list(games['open_games'])
                    current_menu = multiplayer_games_menu
                    continue

            # Server name input
            elif current_menu == multiplayer_server_name_input:
                if cmd == MENU_INPUT_SUBMIT:
                    multiplayer_server_name_input.submit()
                    current_menu = new_multiplayer_menu
                    # Connect
                elif cmd == MENU_INPUT_CANCEL:
                    current_menu = new_multiplayer_menu

                continue

            # Player name input
            elif current_menu == multiplayer_player_name_input:
                if cmd == MENU_INPUT_SUBMIT:
                    multiplayer_player_name_input.submit()
                    current_menu = new_multiplayer_menu
                elif cmd == MENU_INPUT_CANCEL:
                    current_menu = new_multiplayer_menu

                continue

            # Create-new-game name input
            elif current_menu == multiplayer_game_name_input:
                if cmd == MENU_INPUT_SUBMIT:
                    multiplayer_game_name_input.submit()
                    # Connect to server, create game
                    if mreactor is None:
                        mreactor = Reactor(
                            multiplayer_server_name_input.value,
                            multiplayer_player_name_input.value,
                        )
                    mreactor.create_game(multiplayer_game_name_input.value)
                    log.debug("Game created")

                    # Update games list, go to game list menu
                    games = mreactor.list_games()
                    multiplayer_games_menu.update_games_list(games['open_games'])
                    current_menu = multiplayer_games_menu

                elif cmd == MENU_INPUT_CANCEL:
                    current_menu = new_multiplayer_menu

                continue

            # Game name input
            elif current_menu == multiplayer_games_menu:
                if cmd == MENU_LBOX_UP:
                    multiplayer_games_menu.scroll_up()
                elif cmd == MENU_LBOX_DN:
                    multiplayer_games_menu.scroll_down()
                elif cmd == MENU_INPUT_CANCEL:
                    current_menu = new_multiplayer_menu
                elif cmd in xrange(MENU_GAME_1, MENU_GAME_5 + 1):
                    # A running game has been selected
                    game_name = multiplayer_games_menu.get_game_name(cmd)
                    game_name = str(game_name)
                    log.info("Game %s selected" % game_name)

                    res = mreactor.join_game(game_name)
                    quit = game.Main_Loop(screen, clock,
                         (width,height), None, MENU_PEACEFUL, mreactor=mreactor)
                    game.multiplayer = mreactor



            else: # Load menu
                if ( cmd >= 0 ):
                    # Start game from saved position
                    quit = game.Main_Loop(screen, clock, 
                            (width,height), cmd, None)

            current_menu = main_menu

    return True

def Update_Feature(screen, menu_image):
    def Message(msg_list):
        screen.blit(menu_image, (0,0))

        y = screen.get_rect().centery
        for msg in msg_list:
            img_1 = stats.Get_Font(24).render(msg, True, (255, 255, 255))
            img_2 = stats.Get_Font(24).render(msg, True, (0, 0, 0))
            img_r = img_1.get_rect()
            img_r.centerx = screen.get_rect().centerx
            img_r.centery = y
            screen.blit(img_2, img_r.topleft)
            screen.blit(img_1, img_r.move(2,-2).topleft)
            y += img_r.height
        pygame.display.flip()

    def Finish(cerror=None):
        if ( cerror != None ):
            Message(["Connection error:", cerror])

        ok = True
        timer = 4000
        while (( ok ) and ( timer > 0 )):
            e = pygame.event.poll()
            while ( e.type != NOEVENT ):
                if (( e.type == MOUSEBUTTONDOWN )
                or ( e.type == KEYDOWN )
                or ( e.type == QUIT )):
                    ok = False
                e = pygame.event.poll()

            pygame.time.wait( 40 )
            timer -= 40
   
    Message(["Connecting to Website..."])
    url = ( CGISCRIPT + "a=1" )
    new_version = None
    try:
        f = urllib.urlopen(url)
        new_version = f.readline()
        f.close()
    except Exception, x:
        Finish(str(x))
        return False

    if (( new_version == None )
    or ( type(new_version) != str )
    or ( len(new_version) < 2 )
    or ( len(new_version) > 10 )
    or ( not new_version[ 0 ].isdigit() )
    or ( new_version.find('.') <= 0 )):
        Finish("Version data not found.")
        return False

    new_version = new_version.strip()

    # Protect user from possible malicious tampering
    # via a man-in-the-middle attack. I don't want to 
    # render an unfiltered string.
    for i in new_version:
        if (( i != '.' )
        and ( i != '-' )
        and ( not i.isdigit() )
        and ( not i.isalpha() )):
            Finish("Version data is incorrect.")
            return False

    if ( new_version == startup.Get_Game_Version() ):
        Message(["Your software is up to date!",
            "Thankyou for using the update feature."])
        Finish(None)
        return False

    Message(["New version " + new_version + " is available!",
            "Opening website..."])
    Finish(None)
    return True




