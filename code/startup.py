# 
# 20,000 Light Years Into Space
# This game is licensed under GPL v2, and copyright (C) Jack Whitham 2006.
# 

# Version check. This file can be much shorter for Debian.

__version__ = '2.0.0-alpha'

def Get_Game_Version():
    return __version__

def Main(data_dir, ignore = None):
    import main
    main.Main(data_dir)


