import logging
import queue
import random

from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.endpoints import connectProtocol
from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall

from net.p2pproto import P2pProto
from .messagefactory import MessageFactory
from .utils import get_random_id

logger = logging.getLogger(__name__)

# at what frequency to update local blockchain
BLOCKCHAIN_SYNCHRONIZE_INTERVAL_SECONDS = 5
# at what frequency to catch-up (try and get new blocks)
CATCHUP_SYNCHRONIZE_INTERVAL_SECONDS = 600


class P2pFactory(Factory):
    """Twisted protocol factory for FumbleChain"""

    def __init__(self, magic, blockq, txq, bc, port, maxpeers=0):
        """
        @msgfactory: the message factory
        @maxpeers: max peers to connect to (0 == no limit)
        """
        self.magic = magic
        self.blockq = blockq
        self.txq = txq
        self.bc = bc
        self.port = port
        self.msgfactory = MessageFactory(magic)
        self.maxpeers = maxpeers
        self.id = get_random_id()
        # {P2pProto: Peer}
        self.nodes = {}
        self.bc_synchronizer = LoopingCall(self.synchronize_blockchain)
        self.catchup_synchronizer = LoopingCall(self.catch_up)

    def startFactory(self):
        """Interface - called before connecting"""
        logger.info("Starting factory...")
        logger.info("this node id: {}".format(self.id))
        logger.info("Starting local blockchain synchronizer...")
        self.bc_synchronizer.start(BLOCKCHAIN_SYNCHRONIZE_INTERVAL_SECONDS)

    def start_catchup_looping_call(self):
        """Start the catchup LoopingCall"""
        try:
            self.catchup_synchronizer.start(CATCHUP_SYNCHRONIZE_INTERVAL_SECONDS)
            logger.debug("[catch-up] started catchup LoopingCall")
        except AssertionError:
            logger.debug("catchup LoopingCall is already started")

    def stopFactory(self):
        """Interface - called when disconnected"""
        logger.info("Stopping factory...")

    def buildProtocol(self, address):
        """Tell the factory to use the P2pProto class to handle new connections."""
        logger.debug('new protocol for {}'.format(address))
        return P2pProto(self, client=False)

    def broadcast(self, data):
        """Broadcast raw data to all peers
        @data should be a valid serialized message
        """
        for proto in self.nodes.keys():
            proto.send_raw(data)

    def broadcast_block(self, block):
        """Broadcast block to all peers"""
        for proto in self.nodes.keys():
            proto.send_block(block)

    def broadcast_tx(self, tx):
        """Broadcast transaction to all peers"""
        for proto in self.nodes.keys():
            proto.send_tx(tx)

    def _get_node_ids(self):
        """Return IDs of all peers"""
        return [node.id for node in self.nodes.values()]

    @staticmethod
    def connect(host, port, factory):
        """Connect to remote host using factory"""
        logger.info('connecting to {}:{}'.format(host, port))
        proto = P2pProto(factory, client=True)
        r = TCP4ClientEndpoint(reactor, host, int(port), timeout=5)
        d = connectProtocol(r, proto)

    def connect_to(self, id, host, port):
        """Try to connect to a new peer"""
        if id in self._get_node_ids():
            logger.debug("\talready connected to {}".format(id))
        elif id == self.id:
            logger.debug("\tthis is me, ignoring: {}".format(id))
        else:
            nb = len(self.nodes)
            if nb >= self.maxpeers > 0:
                logger.debug("\tignoring peer: {}".format(id))
            else:
                logger.debug("\tconnecting to new peer: {}".format(id))
                P2pFactory.connect(host, port, self)

    def synchronize_blockchain(self):
        """Get transactions and blocks from queues and insert them into the local blockchain
        so that it is always up to date."""
        while True:
            try:
                tx, peer = self.txq.get(block=False, timeout=1)
                logger.debug(f"tx, type({type(tx)})")
                logger.debug(tx)
                logger.debug("Updating local blockchain with tx...")
                success = self.bc.add_transaction(tx)
                logger.debug(f"tx update success: {success}")
            except queue.Empty:
                break

        while True:
            try:
                block, peer = self.blockq.get(block=False, timeout=1)
                # test if block is known
                if block.get_hash() == self.bc.get_block_from_index(-1).get_hash():
                    # this is already our latest known block
                    logger.debug("popped block is latest known block")
                    continue

                logger.debug(f"block, type({type(block)}):")
                logger.debug(block)
                logger.debug("Updating local blockchain with block...")
                success = self.bc.discard_block(block)
                logger.debug(f"block update success: {success}")

                if success:
                    # broadcast block
                    self.broadcast_block(block)
                else:
                    # send REJECT if not outdated
                    top_block = self.bc.get_block_from_index(-1)
                    if block.index > top_block.index + 1:
                        self.catch_up()
                    else:
                        peer.send_reject(block.get_hash())
            except queue.Empty:
                break

    def catch_up(self):
        """Ask for new blocks to a random peer."""
        try:
            # select random peer
            random_peer = random.choice(list(self.nodes.keys()))
            last_block = self.bc.get_block_from_index(-1)

            # catch up from randomly selected peer
            random_peer.send_getblocks(last_block)
        except IndexError:
            logger.debug("Not connected to any peer yet, cannot catch-up.")
