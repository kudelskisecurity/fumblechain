"""
author: ADG

p2p core
"""

import logging

from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.task import LoopingCall
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

from .p2pfactory import P2pFactory

logger = logging.getLogger(__name__)

# max peers to connect to
MAX_PEERS = 300
# how frequently to save the blockchain to disk in seconds
BLOCKCHAIN_SAVE_INTERVAL_SECONDS = 5 * 60


class P2p:
    """P2p core class"""

    def __init__(self, port, addresses, magic, blockq, txq, bc, api_app, api_port, explorer_enabled, explorer_app,
                 explorer_port, bc_path):
        """
        @port: the port to listen to
        @addresses: list of addresses to connect to
        @magic: blockchain magic
        """
        self.port = int(port)
        self.addresses = addresses
        self.api_app = api_app
        self.api_app.p2p = self
        self.api_port = api_port
        self.explorer_app = explorer_app
        self.explorer_enabled = explorer_enabled
        self.explorer_app.p2p = self
        self.explorer_port = explorer_port
        self.bc = bc
        self.bc_path = bc_path
        self.magic = magic
        self.factory = P2pFactory(magic, blockq, txq, bc, self.port, maxpeers=MAX_PEERS)
        self.bc_saver = LoopingCall(self.save_bc)

    def _connect(self, address):
        """Connect to a peer at given address"""
        host, port = address.address
        P2pFactory.connect(host, port, self.factory)

    def start(self):
        """Start this p2p node:
          * Listen to incoming connections
          * Connect to initial peers
          * Start the REST API
          * Start the explorer (optional)
        """
        # start the server
        s = TCP4ServerEndpoint(reactor, self.port)
        s.listen(self.factory)
        logger.info("[p2p] server listening")
        logger.info(f"Magic: {self.magic}")

        # connect to peers
        for address in self.addresses:
            self._connect(address)

        # setup the API
        logger.info("[api] Starting clientAPI on port {}...".format(self.api_port))
        api_resource = WSGIResource(reactor, reactor.getThreadPool(), self.api_app)
        api_site = Site(api_resource)
        reactor.listenTCP(self.api_port, api_site)

        # setup the explorer
        if self.explorer_enabled:
            logger.info("[api] Starting explorer on port {}...".format(self.explorer_port))
            explorer_resource = WSGIResource(reactor, reactor.getThreadPool(), self.explorer_app)
            explorer_site = Site(explorer_resource)
            reactor.listenTCP(self.explorer_port, explorer_site)

        # start the reactor
        logger.info("[p2p] reactor started")
        self.bc_saver.start(BLOCKCHAIN_SAVE_INTERVAL_SECONDS, now=False)
        reactor.run()

    def stop(self):
        """Stop this p2p node"""
        logger.info('[p2p] stopping reactor')
        self.save_bc()  # save blockchain to disk

    def save_bc(self):
        """Save blockchain to disk"""
        logger.info("Saving blockchain to disk...")
        self.bc.save_to_file(self.bc_path)

    def broadcast_block(self, block):
        """Broadcast block to all peers"""
        logger.debug("broadcasting block")
        self.factory.broadcast_block(block)

    def broadcast_tx(self, tx):
        """Broadcast transaction to all peers"""
        logger.debug("broadcasting tx")
        self.factory.broadcast_tx(tx)
