#!/usr/bin/env python
# Copyright (C) 2012 Federico Ceratto <federico.ceratto@gmail.com>
# This file is licensed under GPL v2

from argparse import ArgumentParser
from time import time
import json
import logging
import struct # for packing integers
import zmq

from network import generate_map, get_closest
from primitives import distance

log = logging.getLogger('server')


def setup_logging(debug):
    ch = logging.StreamHandler()
    if debug:
        log.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(name)s %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

def parse_args():
    """Parse CLI options
    :returns: args
    """
    p = ArgumentParser()
    p.add_argument('-v', '--verbose', default=False,
        help="verbose mode", action="store_true")
    #p.add_argument('-p', '--port',
    #    help="network port")
    args = p.parse_args()
    return args

class UserException(Exception):
    pass

class KVMsg(object):
    """
    Message is formatted on wire as 3 frames:
    frame 0: key (0MQ string)
    frame 1: sequence (8 bytes, network order)
    frame 2: body (blob)
    """
    key = None # key (string)
    sequence = 0 # int
    body = None # blob

    def __init__(self, sequence, key=None, body=None):
        assert isinstance(sequence, int)
        self.sequence = sequence
        self.key = key
        self.body = body

    def send(self, socket):
        """Send key-value message to socket; any empty frames are sent as such."""
        key = '' if self.key is None else self.key
        seq_s = struct.pack('!l', self.sequence)
        body = json.dumps(self.body)
        socket.send_multipart([key, seq_s, body])

    @classmethod
    def recv(cls, socket):
        """Reads key-value message from socket, returns new kvmsg instance."""
        key, seq_s, body = socket.recv_multipart()
        key = key if key else None
        seq = struct.unpack('!l',seq_s)[0]
        body = body if body else None
        return cls(seq, key=key, body=body)

    def dump(self):
        if self.body is None:
            size = 0
            data='NULL'
        else:
            size = len(self.body)
            data=repr(self.body)
        log.debug("[seq:{seq}][key:{key}][size:{size}] {data}".format(
            seq=self.sequence,
            key=self.key,
            size=size,
            data=data,
        ))

    def __repr__(self):
        """ """
        try:
            return json.dumps(self.body, indent=1, sort_keys=True)
        except TypeError:
            return self.__repr__()

# simple struct for routing information for a key-value snapshot
class Route:
    def __init__(self, socket, identity, subtree):
        self.socket = socket # ROUTER socket to send to
        self.identity = identity # Identity of peer who requested state
        self.subtree = subtree # Client subtree specification


class Server(object):
    def __init__(self):
        """Initialize sockets"""
        self._sigint_time = 0

        # context and sockets
        ctx = zmq.Context()
        self._snapshot = ctx.socket(zmq.ROUTER)
        self._snapshot.bind("tcp://*:5556")
        self._publisher = ctx.socket(zmq.PUB)
        self._publisher.bind("tcp://*:5557")
        self._collector = ctx.socket(zmq.PULL)
        self._collector.bind("tcp://*:5558")

        # Request/reply socket to execute commands
        self._requester = ctx.socket(zmq.REP)
        self._requester.bind("tcp://*:5555")

        # Broadcast channel
        self._broadcast = ctx.socket(zmq.PUB)
        self._broadcast.bind("tcp://*:5559")

        self._sequence = 0
        self._kvmap = {}

        self._poller = zmq.Poller()
        self._poller.register(self._collector, zmq.POLLIN)
        self._poller.register(self._snapshot, zmq.POLLIN)
        self._poller.register(self._requester, zmq.POLLIN)
        log.info("Sockets created")

        # Game items
        self._games = {}

    def run(self):
        """Run endless loop"""
        log.info("Starting loop")
        while True:
            try:
                items = dict(self._poller.poll(10000))
                if self._collector in items:
                    # Apply state update sent from client
                    self._process_client_updates()

                if self._snapshot in items:
                    self._perform_snapshot()

                if self._requester in items:
                    self._process_client_commands()

            except KeyboardInterrupt:
                if time() > self._sigint_time + .2:
                    # Dump datastore on Ctrl-C
                    #print(self._pprint_datastore())
                    for g in self._games.itervalues():
                        for k in sorted(g):
                            v = g[k]
                            if isinstance(v, dict):
                                for k2, v2 in v.iteritems():
                                    print " ", k2, v2
                                print k, v

                    self._sigint_time = time()
                else:
                    log.info("Exiting")
                    self._collector.close()
                    self._publisher.close()
                    break


    def _process_client_updates(self):
        """Process client updates"""
        log.debug("Processing update")
        kvmsg = KVMsg.recv(self._collector)
        self._sequence += 1
        kvmsg.sequence = self._sequence
        kvmsg.send(self._publisher)
        self._kvmap[kvmsg.key] = json.loads(kvmsg.body)

    def _update_store(self, k, v):
        """Update the store and send an update message to the clients"""
        self._sequence += 1
        #FIXME



    def _pprint_datastore(self):
        """Pretty-print datastore contents"""
        try:
            return json.dumps(self._games, indent=1, sort_keys=True)
        except Exception, e:
            print e
            return 'not printable'

    def _perform_snapshot(self):
        """Perform snapshot"""
        msg = self._snapshot.recv_multipart()
        identity, request, subtree = msg

        if request == "SNAPSHOT":
            # Send state snapshot to client
            route = Route(self._snapshot, identity, subtree)
            self._send_store(route)

        else:
            log.error("Unknown request: %s" % repr(request))

    # New methods

    def _broadcast_update(self, game_name, payload):
        """Broadcast an update to any connected client"""
        log.debug("Broadcasting update: %s" % repr(payload))
        msg = "%s %s" % (game_name, json.dumps(payload))
        self._broadcast.send_unicode(msg)

    def _process_client_commands(self):
        """Process client commands: snapshots, purge..."""
        msg = self._requester.recv_multipart()
        try:
            msg = json.loads(msg[0])
            name = msg['name']
            params = msg['params']
            client_name = msg['client_name']
            timestamp = msg['timestamp']
        except Exception, e:
            log.error(e, exc_info=True)
            return

        log.debug("Processing %s %s" % (name, repr(params)))

        # Route method call
        try:
            method = getattr(self, "_routed_%s" % name)
            result = method(client_name, params, timestamp)
            if result is None:
                result = {'status': 'ok'}
            self._requester.send(json.dumps(result))
        except AttributeError:
            #FIXME: masks other AttributeError exceptions
            log.error("Unknows command called: %s" % name)
        except UserException, e:
            self._requester.send(json.dumps({
                'status': 'error',
                'error_msg': str(e),
            }))
        except Exception, e:
            log.error("Unhandled exception.", exc_info=True)
            self._requester.send(json.dumps({
                'status': 'error',
                'error_msg': "Server-side exception: %s " %str(e),
            }))



    def _routed_get_store_repr(self, player_name, params, tstamp):
        return self._pprint_datastore()


    def _routed_purge_players(self, player_name, params, tstamp):
        """Purge timed-out players"""
        log.info("Purging store")
        for cnt in xrange(1, 1):
            p = "%splayer%d" % (subtree, cnt)
            if p not in self._kvmap:
                continue
            last_t = float(self._kvmap["%shearthbeat" % p].body)
            if last_t + 3 < time():
                # timed out player
                log.debug("  Player %s timed out" % p)
                for k in self._kvmap.keys():
                    if k.startswith(p):
                        log.debug("    Purging %s" % k)
                        del(self._kvmap[k])

        return {}


    def _routed_create_game(self, player_name, params, tstamp):
        """Create new game"""
        game_name = params['game_name']
        max_players = params['max_players']
        min_dist_between_cities = params['min_dist_between_cities']
        max_building_distance = params['max_building_distance']
        if game_name in self._games:
            raise UserException('Game already exists.')

        cities, rocks, wells = generate_map(max_players, min_dist_between_cities)

        self._games[game_name] = {
            'name': game_name,
            'players': {},
            'status': 'not running',
            'creation_time': time(),
            'max_players': max_players,
            'static_map': {
                'cities': cities,
                'rocks': rocks,
                'wells': wells,
            },
            'pipes': {},
            'nodes': {},
            'unowned_cities': list(cities),
            'max_building_distance': max_building_distance,
        }

    def _routed_get_static_map(self, player_name, params, tstamp):
        """Get static map"""
        game_name = params['game_name']
        return {
            'status': 'ok',
            'static_map': self._games[game_name]['static_map'],
        }

    def _remove_expired_games(self):
        """Remove expired games"""
        for name, game in self._games.items():
            if game['status'] == 'not running' \
                and game['creation_time'] < time() - 1000:
                del(self._games[name])
                log.info("Expiring '%s' game" % name)

    def _routed_list_games(self, player_name, params, tstamp):
        """List existing games"""
        open_games = [g['name'] for g in self._games.itervalues() if g['status'] == 'not running']
        running_games = [g['name'] for g in self._games.itervalues() if g['status'] == 'running']
        return {
            'status': 'ok',
            'open_games': open_games,
            'running_games': running_games,
        }

    def _routed_join_game(self, player_name, params, tstamp):
        """Join an existing game"""
        game_name = params['game_name']
        try:
            game = self._games[game_name]
            players = game['players']
        except KeyError:
            raise UserException('Game not found. Maybe it expired.')

        if player_name in players:
            city = players[player_name]['city']
        else:
            # Pick a city for the new player
            if not game['unowned_cities']:
                raise UserException('Maximum number of players reached.')

            city = game['unowned_cities'].pop()

            # create player structure
            players[player_name] = {
                'name': player_name,
                'score': 0,
                'city': city,
            }

            # announce new player
            self._broadcast_update(game_name, {
                'event': 'new_player',
                'player_name': player_name,
            })

        return {
            'status': 'ok',
            'city': city,
            'max_building_distance': self._games[game_name]['max_building_distance'],
            'max_players': self._games[game_name]['max_players'],
            'players': players,
        }


    def _routed_add_node(self, player_name, params, tstamp):
        """Place new node"""
        game_name = params['game_name']
        game = self._games[game_name]
        node = tuple(params['node'])
        if node in game['nodes']:
            raise UserException('occupied')

        game['nodes'][node] = {'owner': None, 'status': None}
        log.debug("%s added a node" % player_name)
        self._broadcast_update(game_name, {
            'event': 'new_node',
            'player_name': player_name,
            'position': node,
        })


        return
        #
        # The following code is disabled: the check is performed on client side
        #
        # Ensure that the node is close enough to another node owned by the
        # player
        #mbd = game['max_building_distance']
        #for npos, ndict in game['nodes'].iteritems():
        #    if ndict['owner'] != player_name:
        #        continue
        #    #TODO: the distance should be measured on an isometric surface
        #    if distance(node, npos) < mbd:
        #        # Found an owned node in the proximity
        #        game['nodes'][node] = {'owner': None, 'status': None}
        #        log.debug(distance(node, npos))
        #        return

        ## No close node has been found
        #raise UserException('toofar')

    def _routed_set_finished_node(self, player_name, params, tstamp):
        """Set node as finished building"""
        game_name = params['game_name']
        game = self._games[game_name]
        node = tuple(params['node'])

        if node is not game['nodes']:
            #HACK
            game['nodes'][node] = {'owner': player_name, 'status': 'built'}
            #raise UserException('notfound')

        # Set nodes status
        if game['nodes'][node]['status'] == 'building':
            gn[start_node]['status'] = 'built'

    def _routed_delete_node(self, player_name, params, tstamp):
        """Delete an existing node"""
        game_name = params['game_name']
        game = self._games[game_name]
        node = tuple(params['node'])
        try:
            n = game['nodes'][node]
        except KeyError:
            raise UserException('notfound')

        if n['owner'] not in (None, player_name):
            raise UserException('notowned')

        del(game['nodes']['node'])

    def _routed_add_pipe(self, player_name, params, tstamp):
        """Place a new pipe"""
        game_name = params['game_name']
        game = self._games[game_name]
        start_node, end_node = map(tuple, params['nodes'])
        gn = game['nodes']

        if start_node not in gn:
            log.error("%s not in %s" % (repr(start_node), repr(gn)))
            raise UserException('missing_endpoint')
        if end_node not in gn:
            log.error("%s not in %s" % (repr(end_node), repr(gn)))
            raise UserException('missing_endpoint')

        st_ow = gn[start_node]['owner']
        end_ow = gn[end_node]['owner']

        #if st_ow not in (None, player_name) or \
        #    end_ow not in (None, player_name):
        #    raise UserException('not_owned')

        #if st_ow == player_name and gn[start_node]['status'] == 'built' or \
        #    end_ow == player_name and gn[end_node]['status'] == 'built':
        #    pass # the user owns at least one fully-built endpoint
        #else:
        #    raise UserException('not_owned')

        # Add pipe
        game['pipes'][(start_node, end_node)] = {
            'owner': player_name,
        }

        # Gain node ownership
        if gn[start_node]['owner'] != player_name:
            gn[start_node]['owner'] = player_name
            gn[start_node]['status'] = 'building'

        if gn[end_node]['owner'] != player_name:
            gn[end_node]['owner'] = player_name
            gn[end_node]['status'] = 'building'


        log.debug("%s added a pipe" % player_name)
        self._broadcast_update(game_name, {
            'event': 'new_pipe',
            'owner': player_name,
            'start_node': start_node,
            'end_node': end_node,
        })

    def _routed_set_finished_pipe(self, player_name, params, tstamp):
        """Finish building a pipe"""
        game_name = params['game_name']
        game = self._games[game_name]
        start_node, end_node = params['nodes']
        gn = game['nodes']

        if start_node not in gn or end_node not in gn:
            raise UserException('missing_endpoint')

        if gn[start_node]['owner'] != player_name or \
            gn[end_node]['owner'] != player_name:
            raise UserException('not_owned')

        # Set nodes status
        if gn[start_node]['status'] == 'building':
            gn[start_node]['status'] = 'built'
        if gn[end_node]['status'] == 'building':
            gn[end_node]['status'] = 'built'

    def _routed_delete_pipe(self, player_name, params, tstamp):
        """Delete an existing pipe"""
        game_name = params['game_name']
        game = self._games[game_name]
        start_node, end_node = params['nodes']
        gn = game['nodes']

    def _routed_leave_game(self, player_name, params, tstamp):
        """A player leaves the game due to victory, loss or abandon"""
        game_name = params['game_name']
        reason = params['reason']
        # reason: victory, steam_loss, None

        self._broadcast_update(game_name, {
            'event': 'player_leaves',
            'player_name': player_name,
            'reason': reason,
        })

        game = self._games[game_name]
        log.debug("%s: %s declared %s" % (game_name, player_name, reason))
        if reason == 'victory':
            del(self._games[game_name])
        else:
            # The player abandoned or lost
            del(game['players'][player_name])
            if len(game['players']) == 1:
                # only one player left. The player wins.
                winner = game['players'][0]
                self._broadcast_update(game_name, {
                    'event': 'player_leaves',
                    'player_name': winner,
                    'reason': 'victory',
                })
                del(self._games[game_name])
            elif len(game['players']) == 0:
                # No players left, just delete the game.
                del(self._games[game_name])





    def _routed_broadcast(self, player_name, params, tstamp):
        """Broadcast messages from a player"""
        game_name = params['game_name']
        #game = self._games[game_name]
        msg = params['msg']
        self._broadcast_update(game_name, msg)

    def _send_store(self, route):
        """Send a state snapshot to a socket"""
        # For each entry in kvmap, send kvmsg to client
        msg = KVMsg(self._sequence)
        for k,v in self._kvmap.iteritems():
            if k.startswith(route.subtree):
                msg.key = k
                msg.body = v
                msg.send(self._snapshot)
                route.socket.send(route.identity, zmq.SNDMORE)
                msg.send(route.socket)


    def _send_single(self, key, kvmsg, route):
        """Send one state snapshot key-value pair to a socket"""
        # check front of key against subscription subtree:
        msg = KVMsg(self._sequence)
        msg.key = key
        msg.body = 'null'
        msg.send(self._snapshot)

        if kvmsg.key.startswith(route.subtree):
            # Send identity of recipient first
            route.socket.send(route.identity, zmq.SNDMORE)
            kvmsg.send(route.socket)


from threading import Thread

class AutoRestarter(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._mtime = self._my_mtime()
        log.debug('monitoring %s' % __file__)

    def _my_mtime(self):
        from os.path import getmtime
        return getmtime(__file__)

    def run(self):
        log.debug('running restarter')
        from sys import exit
        from time import sleep
        from thread import interrupt_main
        import os
        import signal
        while True:
            sleep(1)
            t = self._my_mtime()
            if self._mtime != t:
                log.info('file %s changed: exiting' % __file__)
                os.kill(os.getpid(), signal.SIGINT)
                sleep(.05)
                os.kill(os.getpid(), signal.SIGINT)
                exit(1)


def main():
    args = parse_args()
    setup_logging(args.verbose)
    #AutoRestarter().start()
    server = Server()
    server.run()

if __name__ == '__main__':
    main()
