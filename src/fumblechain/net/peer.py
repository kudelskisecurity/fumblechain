"""
author: ADG

represent a remote peer
"""

import datetime
import json

from utils.serde import Encoder


class Peer:
    """Represents a peer, connected to the same FumbleChain network as us"""

    def __init__(self, address, id=None, client=True):
        """
        @address: the (ip, port) pair
        @id: the node id (if any)
        @client: did we connect to it ?
        """
        self.address = address
        self.id = id
        self.client = client
        self.lastseen = None

    def seen(self):
        """Update last seen time for this peer"""
        self.lastseen = datetime.datetime.utcnow()

    def not_seen_for(self):
        """Return the number of seconds elapsed since we have last seen this peer"""
        if not self.lastseen:
            return -1
        now = datetime.datetime.utcnow()
        return (now - self.lastseen).total_seconds()

    def __str__(self):
        ip, port = self.address
        return "peer {}:{} (client:{})".format(ip, port, self.client)

    def _serialize(self):
        fields = {
            "address": self.address,
            "id": self.id,
            "client": self.client,
            "lastseen": self.lastseen.isoformat()
        }
        return fields

    def to_json(self):
        return json.dumps(self, cls=Encoder)
