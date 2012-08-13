# Copyright (C) 2012 Federico Ceratto <federico.ceratto@gmail.com>
# This file is licensed under GPL v2

import struct
import sys
import json
from time import time, sleep
from threading import Thread

import zmq

import logging as log
log.basicConfig(format='%(levelname)s %(message)s', level=log.DEBUG)

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
        socket.send_multipart([ key, seq_s, body ])

    @classmethod
    def recv(cls, socket):
        """Reads key-value message from socket, returns new kvmsg instance."""
        key, seq_s, body = socket.recv_multipart()
        key = key if key else None
        seq = struct.unpack('!l',seq_s)[0]
        body = json.loads(body)
        return cls(seq, key=key, body=body)

    def dump(self):
        if self.body is None:
            size = 0
            data='NULL'
        else:
            size = len(self.body)
            data=repr(self.body)
        print >> sys.stderr, "[seq:{seq}][key:{key}][size:{size}] {data}".format(
            seq=self.sequence,
            key=self.key,
            size=size,
            data=data,
        )


class Reactor(object):

    def __init__(self, server, subtree, username, wait=True):
        """ """
        self._kvmap = {}
        self._changed_keys = []
        self._running = True
        self._subtree = subtree + '/'
        self._hearthbeat_time = 0
        self.role = None

        # Prepare our context and subscriber
        ctx = zmq.Context()
        self._snapshot = ctx.socket(zmq.DEALER)
        self._snapshot.linger = 0
        self._snapshot.connect("tcp://%s:5556" % server)
        self._subscriber = ctx.socket(zmq.SUB)
        self._subscriber.linger = 0
        self._subscriber.setsockopt(zmq.SUBSCRIBE, self._subtree)
        self._subscriber.connect("tcp://%s:5557" % server)
        self._publisher = ctx.socket(zmq.PUB)
        self._publisher.linger = 0
        self._publisher.connect("tcp://%s:5558" % server)

        self._requester = ctx.socket(zmq.REQ)
        self._requester.linger = 0
        self._requester.connect("tcp://%s:5555" % server)

        self._poller = zmq.Poller()
        self._poller.register(self._subscriber, zmq.POLLIN)

        self.role = username
        return


        #-----------------------

        # Purge timed out players
        # self._remote_purge()

        # Get state snapshot
        self._sequence = 0
        self._snapshot.send_multipart(["SNAPSHOT", self._subtree])

        log.debug("Fetching snapshot")
        while self._running:
            kvmsg = self._receive(self._snapshot)

            if kvmsg.key == "KTHXBAI":
                self._sequence = kvmsg.sequence
                break # Done

            self._insert_from_msg(kvmsg)


        self.update()

        # Populate store
        player_names = ["player%d" % cnt for cnt in xrange(1, 10)]
        for p in player_names:
            if p not in self._kvmap.keys():

                self._snapshot.send_multipart(["setup_player", self._subtree])

                self[p] = username
                self.role = p
                log.debug("Logged in as %s" % self.role)
                break


        self[self.role + 'nodes'] = []
        self[self.role + 'pipes'] = []
        self[self.role + "hearthbeat"] = time()
        self.update()

        # Start hearthbeat
        #log.debug("Starting hearthbeat")
        #Thread(target=self._hearthbeat).start()
        log.debug("Dump")
        self._remote_dump()

        if wait:
            players_num = sum([p in self for p in player_names])
            while players_num < 2:
                print "Waiting for second player to join..."
                sleep(1)
                self.update()
                players_num = sum([p in self for p in player_names])

            log.info("Player 2 \"%s\" has joined" % self['player2'])

    def _call(self, name, d):
        """Send a syncronous request to the server"""
        request = {
            'name': name,
            'params': d,
            'client_name': self.role,
            'timestamp': time(),
        }
        self._requester.send(json.dumps(request))
        resp = json.loads(self._requester.recv())
        if resp is None or resp.get('status', None) == 'ok':
            return resp

        if 'error_msg' in resp:
            raise UserException(resp['error_msg'])

        raise RuntimeError('unspecified')


    def list_games(self):
        return self._call('list_games', {})

    def create_game(self, game_name, min_dist_between_cities=12, max_building_distance=5):
        return self._call('create_game', {
            'game_name': game_name,
            'max_players': 2,
            'min_dist_between_cities': min_dist_between_cities,
            'max_building_distance': max_building_distance,
        })

    def join_game(self, game_name):
        ret = self._call('join_game', {'game_name': game_name})
        self._current_game_name = game_name
        return ret

    def leave_game(self):
        assert self._current_game_name, "leave_game() called while not in a game"
        ret = self._call('leave_game', {'game_name': self._current_game_name})
        self._current_game_name = None
        return ret

    def get_static_map(self):
        assert self._current_game_name, "get_static_map() called while not in a game"
        ret = self._call('get_static_map', {'game_name': self._current_game_name})

        return [ret['static_map'][i] for i in ('cities', 'rocks', 'wells')]

    def add_node(self, node):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('add_node', {
            'game_name': self._current_game_name,
            'node': node,
        })
        return ret

    def set_finished_node(self, node):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('set_finished_node', {
            'game_name': self._current_game_name,
            'node': node,
        })
        return ret

    def delete_node(self, node):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('delete_node', {
            'game_name': self._current_game_name,
            'node': node,
        })
        return ret

    def add_pipe(self, nodes):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('add_pipe', {
            'game_name': self._current_game_name,
            'nodes': nodes,
        })
        return ret

    def set_finished_pipe(self, nodes):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('set_finished_pipe', {
            'game_name': self._current_game_name,
            'nodes': nodes,
        })
        return ret

    def delete_pipe(self, nodes):
        assert self._current_game_name, "Game-related method called while not in a game"
        ret = self._call('delete_pipe', {
            'game_name': self._current_game_name,
            'nodes': nodes,
        })
        return ret

    @property
    def _hearthbeat(self):
        """Update a hearthbeat value"""
        try:
            msg = KVMsg(0)
            k = "%shearthbeat" % self.role
            msg.key = self._subtree + k

            while self._running:
                msg.body = time()
                msg.send(self._publisher)
                sleep(1)

        except KeyboardInterrupt:
            self._running = False

    def _syncronous_hearthbeat(self):
        """Update a hearthbeat value"""
        if self.role and time() > self._hearthbeat_time + 1:
            self._hearthbeat_time = time()
            msg = KVMsg(0)
            k = "%shearthbeat" % self.role
            msg.key = self._subtree + k
            msg.body = time()
            msg.send(self._publisher)


    def _insert_from_msg(self, msg):
        """Update the dict using an incoming msg"""
        if msg.key is not None:
            k = msg.key.lstrip(self._subtree)
            self._kvmap[k] = msg.body

    def update(self):
        return


        """ """
        #log.debug("Update")
        # If some keys have been changed, send them to the server
        for k in self._changed_keys:
            log.debug("Sending %s" % k)
            msg = KVMsg(0)
            msg.key = self._subtree + k
            msg.body = self[k]
            msg.send(self._publisher)

        self._changed_keys = []

        self._syncronous_hearthbeat()

        # Poll incoming messages
        items = dict(self._poller.poll(1))

        if self._subscriber in items:
            kvmsg = KVMsg.recv(self._subscriber)

            # Discard out-of-sequence kvmsgs, incl. heartbeats
            if kvmsg.sequence > self._sequence:
                self._sequence = kvmsg.sequence
                self._insert_from_msg(kvmsg)
                print "I: received update=%d" % self._sequence

    def _receive(self, socket):
        """Receive a key-value message from socket, ."""
        key, seq_s, body = socket.recv_multipart()
        key = key if key else None
        seq = struct.unpack('!l',seq_s)[0]
        body = json.loads(body)
        return KVMsg(seq, key=key, body=body)

    def _remote_dump(self):
        """Print a dump of the datastore on the server side"""
        self._snapshot.send_multipart(["PRINTREPR", self._subtree])

    def _remote_purge(self):
        """Purge the datastore on the server side"""
        self._snapshot.send_multipart(["PURGE", self._subtree])
        self._kvmap = {}




if __name__ == '__main__':
    # test
    r = Reactor('localhost', '1', 'fede', wait=False)
    #r._remote_purge()
    r.update()

    #r._remote_dump()

    try:
        sleep(2)

    except KeyboardInterrupt:
        pass

    r._running = False
    print "END"
