# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006-07.
# 
# 4 hours remaining.
# For a new player, the game is confusing and difficult to understand.
# Solution: tutorial mode.
# Can it be done?

import pygame , time
from pygame.locals import *

import stats , extra , resource
from primitives import *
from map_items import *


__tutor = None

def On(width):
    global __tutor
    __tutor = Tutor_Memory(width)

    set_message(None, "welcome",
        "Welcome to 20,000 Light Years Into Space!",
        """You are playing the interactive tutorial. As you play, information boxes like this one will appear on your screen. When each message appears, read it, and then follow the instructions that it provides.
To proceed, select the City, which is in the centre of the map.""",
        False)


def City_Selected():
    set_message("welcome", "citysel",
        "Your City",
        """To win the game, you must upgrade the city. Upgrades raise the Technology Level of the City. Currently, the City is at level 1 - you can see this on the right hand side of the screen ('Tech Level'). When the City's Tech Level reaches its maximum (depending on the game difficulty), you win.
You can upgrade the City at any time, but you should wait until you have secured some more supplies of steam.
Now click on the structure close to the City.""",
        False)

def Steam_Maker_Selected(first):
    if first:
        set_message("citysel", "steamsel",
            "The First Steam Maker",
            """You have just selected a Steam Maker. Steam Makers are the source of your steam supply. You'll need to build more of these in order to win the game, and you'll need to connect them to your city via Pipes.
Steam Makers have to be built on top of Steam Sources. These are producing clouds of steam - there are about ten of them, dotted around the map.
Click 'Build Node' or 'n', then click on one of the Steam Sources. Ideally, you should choose one that's near the City.""",
            False)
    else:
        set_message("steamsel", "newsteam",
            "The New Steam Maker",
            """You've just planned the construction of a new Steam Maker. It won't actually be built until it is connected by some Pipes to your City.
Your next job is to connect your Steam Maker to your City. For this, you'll need to build a Pipe.
Click 'Build Pipe' or 'p', then click first on the City, and then on the new Steam Maker.""",
            False)

def Pipe_Added():
    set_message("newsteam", "building",
        "Building", 
        """Now you've planned the beginnings of your network. You have two Steam Makers, one operational, the other under construction, and Pipes linking them to the City.
Please wait while the new Steam Maker is built. While construction is in progress, try clicking on the Pipes and the Steam Makers. You'll see some information about them, including the progress of construction.
The gauge on the right shows nodes pressure or pipes flow depending on the selected item.""",
        False)

def All_Nodes_Finished():
    set_message("building", "nodesready",
        "Building Complete!", 
        """Great! Your City is now supplied with Steam from two sources.

Building or upgrading structures requires amounts of metal. Consider building nodes in proximity to some rocks to extract new metal. When planning a new node, a gray area appears around the selected location.
Metal extraction will be carried on automatically withing the gray area at a rate that depends on the rock size and the distance from the node.

You can safely upgrade the City now. Click 'Upgrade' or 'u', and then click on the City. The upgrade will begin immediately.""",
        False)

def City_Upgrade_Running():
    set_message("nodesready", "upgraderunning",
        "Upgrade In Progress",
        """The City upgrade is now in progress. As soon as you started the upgrade, two things happened:
- You got an extra Work Unit. Now two of your buildings can be built simultaneously. Currently, one Work Unit is being used to upgrade the City. The other one is spare.
- The City's steam requirement increased. Note the figures for Supply and Demand on the right hand side. Demand has just gone up. Fortunately, as you have two Steam Makers, Supply will be able to match it.
Now you should strengthen your network. Later in the game, you'll be under attack in a variety of nasty ways. Create a new Node somewhere between the two Steam Makers.
Nodes are just connection points. They store steam, but they don't produce it or consume it.  Different types of buildings are available: basic, hydroponics, research, super and turret nodes. Some provide higher storage capacity and better armor to withstand attacks. Click 'Build Node' or 'n' and then click on the position of your new node.""",
        False)
        
def Node_Selected():
    set_message("upgraderunning", "makinglinks",
        "Making New Links",
        """Your network's strength depends on the number of links. Generally, the more routes between two points, the better. The only disadvantage of adding new routes is that they consume Work Units during construction and repair. Don't worry about that for now.
Now build three new Pipes, each running from your new Node: one to the City, and two for the two Steam Makers. These connections make your network stronger. Wait for these to be built.""",
        False)

def Number_Of_Pipes_Is(pipe_count):
    if pipe_count >= 5:
        set_message("makinglinks", "networkbasics",
            "Almost There...",
            """Excellent. Your network is now strong enough to withstand attacks. You are almost ready to begin playing for real! But before you do, you have to understand how steam flows. Please click on one of the pipes.""",
            False)

def Pipe_Selected():
    set_message("networkbasics", "networkbasics2",
        "Steam is Water..",
        """To understand the network, it helps to imagine that the steam is just (liquid) water. The City is like a drain: it is draining water out of the system. The Steam Makers are like taps: they are adding water to the system. In both cases, the flow rate depends only on the amount of Upgrades you have applied.
Flow rates are given in Flow Units (U). Flow rates are represented by the green dots that move along the pipes. The movement of the dots is proportional to the velocity of the flow.
You open or close a pipe by selecting it and pressing the space bar.
Now click on one of the nodes.""",
        False)

def Any_Node_Selected():
    set_message("networkbasics2", "networkbasics3",
        "Pressure..",
        """Water always finds it's own level. If you have two water tanks and you connect them with a pipe, the water level will try to equalise. The same effect happens here, but with steam.
All of the Nodes are steam storage tanks. The 'level' is steam pressure. It is constantly trying to equalise.
Pressure is given in Pressure Units (P). Now you've selected a Node, you can see its pressure on the right hand side. Pressure is limited: to increase the limit, you can upgrade the node, but there's no need to do that yet.
You lose the game if the pressure at the City falls too low for some time. To avoid that, ensure that Supply matches Demand.
The gauge on the left displays Supply (black hand) and Demand (red hand).
We're almost done. Please click on a pipe again.""",
        False)

def Pipe_Selected_2():
    set_message("networkbasics3", "networkbasics4",
        "Rules Of Thumb",
        """The steam pressures in your Nodes will never equalise, because steam is being added and removed from the network. However, you may wonder why pressure and flow vary so much.
The answer is Resistance. Each pipe has only a limited capacity. There's a limit to the rate at which steam can move, imposed by each pipe. Resistance is a hidden property: you can't see it, but it affects the game. Longer pipes have more resistance than short ones.
All of this will reduce to a few rules of thumb.
- Build one Steam Maker per City Upgrade.
- Make lots of Pipes.
- Don't do an Upgrade unless the steam pressure at your City is stable.
Now you're ready to experience an attack. Please click on your City.""",
        False)

def City_Selected_2():
    set_message("networkbasics4", "attack",
        "Alien Attack",
        """The Aliens are coming!
You can't fight the aliens: all you can do is rebuild your network. They'll try to destroy your Nodes and Pipes: they'll only be able to put your Nodes out of action, but they can destroy your Pipes.
The attack will last for two minutes. If sound is enabled, you will hear an alarm before each wave of alien attackers.
When you're ready for them, click on the planet's surface.""",
    False)

def Nothing_Selected():
    set_message("attack", "running",
        "Alien Attack",
        """Remember:
- Rebuild Pipes that are destroyed by aliens.
- You can add new Pipes, Nodes, and Steam Makers.
- Your goal is always to upgrade the City.
The Aliens disappear after 2 minutes. Good luck.""",
    True)


def Aliens_Gone():
    set_message("running", "ended",
        "You Survived",
        """Good work! You survived the attack.
Now you are ready to play for real. Now click 'Exit to Main Menu' and begin your first game!
Good luck, and have fun.""",
    True)




def Notify_Select(item):
    global __tutor
    if __tutor is None:
        return

    if isinstance(item, Node):
        Any_Node_Selected()


    if isinstance(item, City_Node):
        City_Selected()
        City_Selected_2()
    elif isinstance(item, Well_Node):
        first = item.tutor_special
        Steam_Maker_Selected(first) # note change of terminology :(
    elif isinstance(item, Node):
        Node_Selected()
    elif isinstance(item, Pipe):
        Pipe_Selected()
        Pipe_Selected_2()
    elif item is None:
        Nothing_Selected()

def Notify_Add_Pipe():
    global __tutor
    if __tutor is None:
        return

    Pipe_Added()

def Notify_Add_Node(n):
    global __tutor
    if __tutor is None:
        return

    #Node_Added(n)

def Examine_Game(g):
    global __tutor
    if __tutor is None:
        return

    # test 1 - are all nodes finished?
    all_finished = True
    for n in g.net.node_list:
        all_finished = all_finished and ( not n.Needs_Work() )

    if all_finished:
        All_Nodes_Finished()

    # test 2 - has the city begun an upgrade?
    if g.net.hub.city_upgrade != 0:
        City_Upgrade_Running()

    # test 3 - number of pipes.
    pipe_count = 0
    for p in g.net.pipe_list:
        if (( not p.Is_Destroyed() ) and ( not p.Needs_Work() )):
            pipe_count += 1

    # test 4 - season
    if g.season in [ SEASON_STORM , SEASON_QUAKE ]:
        Aliens_Gone()
        g.game_running = False

    Number_Of_Pipes_Is(pipe_count)

def Off():
    global __tutor
    __tutor = None

def set_message(previous_msg_name, this_msg_name, title, text, sf):
    global __tutor
    if __tutor is not None:
        __tutor.Add_Message((previous_msg_name, this_msg_name,
                title, text, sf))

def Draw(screen, g):
    global __tutor
    t = __tutor
    if t is not None:
        t.Draw(screen, g)

def Permit_Season_Change():
    global __tutor
    t = __tutor
    if t is not None:
        return t.Permit_Season_Change()
    else:
        return True

def Frozen():
    return False

def Active():
    global __tutor
    return ( __tutor is not None )

def Has_Changed():
    global __tutor
    t = __tutor
    if t is not None:
        x = t.update
        t.update = False
        return x
    else:
        return False


class Tutor_Memory(object):
    def __init__(self, w):
        self.current_msg_name = None
        self.current_msg_surf = None
        self.current_msg_popup = False
        self.width = w
        self.update = False
        self.permit_season_change = False
        self._sp_mugshot = sprites.StaticSprite('captain.png', pwidth=120)


    def Add_Message(self,(previous_msg_name, this_msg_name,
                title, text, sf)):

        if self.current_msg_name == previous_msg_name:
            self.current_msg_name = this_msg_name
            self.current_msg_surf = self.__Draw(title, text)
            self.current_msg_popup = True
            self.update = True
            self.permit_season_change = sf

    def Permit_Season_Change(self):
        return self.permit_season_change

    def Draw(self, screen, g):
        if self.current_msg_popup:
            r = self.current_msg_surf.get_rect()
            r.top = r.left = 30
            screen.blit(self.current_msg_surf, r)

    def __Draw(self, title, text):
        """Draw tutorial frame, text and picture."""
        height = 10
        (surf, height) = self.__Draw_H(title, text, height)
        (surf, height) = self.__Draw_H(title, text, height)
        self._sp_mugshot.draw(surf, pcenter=PVector(70, 100))
        return surf

    def __Draw_H(self, title, text, height):
        width = self.width
        top_margin = 10
        title_bottom_margin = 10
        body_bottom_margin = 10
        body_left_margin = 135
        minimum_height = 180
        fs1 = 12
        fs2 = 14
        newline_gap = 12

        surf = pygame.Surface((width, height))
        bbox = surf.get_rect()
        extra.Tile_Texture(surf, "006metal.jpg", bbox)
        
        tsurf = stats.Get_Font(fs1).render(title, True, (250,250,200))
        tsurf_r = tsurf.get_rect()
        tsurf_r.center = bbox.center
        tsurf_r.top = top_margin

        surf.blit(tsurf, tsurf_r.topleft)

        y = tsurf_r.bottom + title_bottom_margin
        # line edging for title
        extra.Line_Edging(surf, Rect(0,0,width,y), True)

        y += top_margin
        x = body_left_margin
        height = y

        # Format and print body
        while len(text):
            newline = False
            i = text.find(' ')
            j = text.find("\n")

            if (( j >= 0 ) and ( j < i )):
                i = j
                newline = True

            if i < 0:
                i = len(text)

            word = text[:i] + " "
            text = text[i+1:].lstrip()

            tsurf = stats.Get_Font(fs2).render(word, True, (250,200,250))
            tsurf_r = tsurf.get_rect()
            tsurf_r.topleft = (x,y)
            if ( tsurf_r.right > (width - 5)):
                # Wrap.
                y += tsurf_r.height
                x = body_left_margin
                tsurf_r.topleft = (x,y)

            surf.blit(tsurf, tsurf_r.topleft)
            x = tsurf_r.right
            height = tsurf_r.bottom + body_bottom_margin
            if height < minimum_height:
                height = minimum_height

            if newline:
                x = body_left_margin
                y = tsurf_r.bottom + newline_gap

        # line edging for rest of box
        extra.Line_Edging(surf, bbox, True)

        return (surf, height)



