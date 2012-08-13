from multiplayer import Reactor
r = Reactor('localhost', '1', 'fede', wait=False)
print r.list_games()
r._running = False

