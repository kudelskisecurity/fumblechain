"""
author: ADG

p2p core
"""

import datetime

from twisted.internet.task import LoopingCall
from twisted.protocols.basic import NetstringReceiver

from .messages import *
from .peer import Peer

logger = logging.getLogger(__name__)

# consider peer as offline if not responded for
PEER_TIMEOUT = 120  # second
# at what frequency to send pings
HEARTBEAT = 60  # second
# query for new peer every
NEW_PEER_REQUEST = 60  # seconds
# how long to keep REJECT states
REJECT_STATE_DURATION_SECONDS = 60


class P2pProto(NetstringReceiver):
    """Twisted protocol for handling connections from other FumbleChain nodes."""
    MAX_LENGTH = 10000000000

    def __init__(self, factory, client=False,
                 heartbeatfreq=HEARTBEAT,
                 newpeerfreq=NEW_PEER_REQUEST):
        """
        @factory: the message factory
        @client: the remote peer we connected to
        @heartbeatfreq: at what frequence to send pings (s)
        @newpeerfreq: at what frequence to ask for new peers (s)
        """
        self.factory = factory
        self.client = client
        self.id = self.factory.id
        self.msgfactory = self.factory.msgfactory
        self.heartbeat = None
        self.heartbeatfreq = heartbeatfreq
        self.getnewpeer = None
        self.newpeerfreq = newpeerfreq
        self.reject_state = []

    def connectionMade(self):
        """Called by framework when connection is made with the remote peer"""
        peer = self.transport.getPeer()  # note that this is the source port, not the listening port
        host = self.transport.getHost()
        logger.debug("connectionMade - peer: {}".format(peer))
        logger.debug("connectionMade - host: {}".format(host))
        logger.debug("client: {}".format(self.client))
        self.address = (peer.host, -1)
        # start by sending version
        self.send_version()

    def connectionLost(self, reason):
        """Called by framework when connection is lost with the remote peer"""
        if self.heartbeat:
            self.heartbeat.stop()
        if self.getnewpeer:
            self.getnewpeer.stop()
        logger.debug("closing connection: {}".format(reason))
        try:
            self.factory.nodes.pop(self)
        except KeyError:
            logger.debug("dropping connection")
        self._print_peers()

    def stringReceived(self, line):
        """Called by framework when data is received"""
        try:
            msg, remote_id = self.msgfactory.deserialize(line)
            self.remote_id = remote_id
            self._receive(msg)
        except DeserializationError as e:
            logger.error("[ERROR] {}".format(e))
            self.disconnect()

    # ###################################################3
    # peer state
    # ###################################################3
    def save_reject_state(self, message_type, block_hash):
        """Keep track of sent MsgBlocks and MsgGetblocks so that
        we can known whether a received MsgReject is genuine or not."""
        # save state in reject state
        now = datetime.datetime.utcnow()
        self.reject_state.append((now, message_type, block_hash))

        # prune old states
        self.prune_reject_state()

    def prune_reject_state(self):
        """Prune old reject states."""
        now = datetime.datetime.utcnow()
        duration = datetime.timedelta(seconds=REJECT_STATE_DURATION_SECONDS)
        time_threshold = now - duration
        self.reject_state = [x for x in self.reject_state if x[0] > time_threshold]

    def is_reject_genuine(self, bhash):
        """Returns True if the received MsgReject message was genuine,
        False otherwise.
        The decision is taken based on stored reject state."""

        # delete old states
        self.prune_reject_state()

        #  check whether we can expect to receive a REJECT from that peer
        for state in self.reject_state:
            dtime, msgcls, block_hash = state
            if block_hash == bhash:
                # this is a block hash for which we may receive a REJECt
                self.reject_state.remove(state)
                return True

        return False

    # ###################################################3
    # senders
    # ###################################################3
    def send_version(self):
        """Send a version message"""
        msg = MsgVersion()
        try:
            payload = self.msgfactory.serialize(msg, self.id, self.factory.port)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_verack(self):
        """Send a verack message"""
        msg = MsgVerack()
        try:
            payload = self.msgfactory.serialize(msg, self.id, **{})
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_ping(self):
        """Send a ping message"""
        msg = MsgPing()
        try:
            payload = self.msgfactory.serialize(msg, self.id, **{})
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_pong(self):
        """Send a pong message"""
        msg = MsgPong()
        try:
            payload = self.msgfactory.serialize(msg, self.id, **{})
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_getaddr(self):
        """Send a getaddr message"""
        msg = MsgGetaddr()
        try:
            payload = self.msgfactory.serialize(msg, self.id, **{})
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_addr(self):
        """Send an addr message"""
        msg = MsgAddr()
        mypeers = []
        for proto, peer in self.factory.nodes.items():
            if peer.not_seen_for() > PEER_TIMEOUT:
                # remove slow/timeouts ones
                proto.disconnect()
                continue
            if peer.id == self.id:
                # ignore myself
                continue
            mypeers.append(peer)
        if not mypeers:
            return
        try:
            payload = self.msgfactory.serialize(msg, self.id, peers=mypeers)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_block(self, block):
        """Send a block"""
        self.save_reject_state(MsgBlock, block.get_hash())
        msg = MsgBlock()
        try:
            payload = self.msgfactory.serialize(msg, self.id, block)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_tx(self, tx):
        """Send a transaction"""
        msg = MsgTx()
        try:
            payload = self.msgfactory.serialize(msg, self.id, tx)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_raw(self, data):
        """Send some already formatted (raw) message"""
        self._send(data)

    def send_reject(self, block_hash):
        """Send a reject message"""
        msg = MsgReject()
        try:
            payload = self.msgfactory.serialize(msg, self.id, block_hash)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_getblocks(self, block):
        """Send a getblocks message"""
        self.save_reject_state(MsgGetblocks, block.get_hash())
        msg = MsgGetblocks()
        topblockhash = block.get_hash()
        try:
            payload = self.msgfactory.serialize(msg, self.id, topblockhash)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    def send_inv(self, blocks):
        """Send an inv message"""
        msg = MsgInv()
        try:
            payload = self.msgfactory.serialize(msg, self.id, objects=blocks, otype=MsgInv.TYPE_BLOCK)
            self._send(payload)
        except SerializationError as e:
            logger.error("[ERROR] {}".format(e))

    # ###################################################3
    # receivers
    # ###################################################3
    def _receive(self, msg):
        """Process received message"""
        logger.info("<--- receiving from {}: {}".format(self.address, msg))

        if msg.COMMAND == "version":
            if not self.client and self.heartbeatfreq > 0:
                # server pings peers
                self.heartbeat = LoopingCall(self.send_ping)
                self.heartbeat.start(self.heartbeatfreq)
            # add timed callback to request for new peers
            self.getnewpeer = LoopingCall(self.send_addr)
            self.getnewpeer.start(self.newpeerfreq)

            # register peer to the factory
            self.address = (self.address[0], msg.port)
            peer = Peer(self.address, id=self.remote_id, client=self.client)
            logger.info("adding node {} as new peer".format(self.remote_id))
            self.factory.nodes[self] = peer
            self.send_verack()
        elif msg.COMMAND == "verack":
            # request for peers
            self.send_getaddr()
            self.factory.start_catchup_looping_call()
        elif msg.COMMAND == "ping":
            # respond to heartbeat
            self.send_pong()
        elif msg.COMMAND == "pong":
            pass
        elif msg.COMMAND == "getaddr":
            # peer request for peers
            self.send_addr()
        elif msg.COMMAND == "addr":
            # new peer address received
            self._parse_addr(msg)
            self._print_peers()
        elif msg.COMMAND == "block":
            # new block is received
            self.factory.blockq.put((msg.block, self))
        elif msg.COMMAND == "tx":
            # new tx is received
            self.factory.txq.put((msg.tx, self))
        elif msg.COMMAND == "getblocks":
            # getblocks is received
            topblockhash = msg.topblockhash
            blocks = self.factory.bc.get_blocks_since(topblockhash)
            if blocks is not None:
                self.send_inv(blocks)
            else:
                self.send_reject(topblockhash)
        elif msg.COMMAND == "inv":
            # inv is received
            blocks = [ot[1] for ot in msg.objects if ot[0] == MsgInv.TYPE_BLOCK]
            logger.debug("what is inside (inv)?")
            for b in blocks:
                logger.debug(b.to_json())

            for b in blocks:
                success = self.factory.bc.discard_block(b)
                if not success:
                    # self.factory.catch_up()
                    break
        elif msg.COMMAND == "reject":
            # reject is received
            block_hash = msg.block_hash

            # pop a block only if it"s not the last
            if len(self.factory.bc.chain) > 1:
                if self.is_reject_genuine(block_hash):
                    top_block = self.factory.bc.get_block_from_index(-1)
                    topblockhash = top_block.get_hash()
                    if topblockhash == block_hash:
                        logger.debug("Genuine REJECT message, popping block")
                        self.factory.bc.pop_block()
                    else:
                        logger.debug(
                            """Genuine REJECT message, but already processed (probably receiving multiple REJECTs from multiple peers after broadcast block)""")
                else:
                    logger.debug(
                        f"Looks like we are under attack! To Arms! (peer: {self.address}, bhash: {block_hash})")
                    self._update_lastseen()
                    return

            self.factory.catch_up()
        # endif
        self._update_lastseen()

    # ###################################################3
    # utils
    # ###################################################3
    def disconnect(self):
        """Disconnect from peer"""
        logger.info("disconnecting from {}".format(self.address))
        self.transport.loseConnection()

    def _send(self, data):
        """Send a message to the remote peer"""
        logger.info("---> sending to {}: {}".format(self.address, data))
        self.sendString("{}\n".format(data).encode())

    def _update_lastseen(self):
        """Update this peer's last seen time"""
        if self in self.factory.nodes:
            peer = self.factory.nodes[self]
            peer.seen()

    def _print_peers(self):
        """Print list of connected peers"""
        logger.debug("[+] peers:")
        for peer in self.factory.nodes.values():
            logger.debug("\t * {} -> {}".format(peer.id, str(peer)))

    def _parse_addr(self, msg):
        """Parse the addr message content and update pool/connect"""
        logger.debug("adding new peers")
        for peer in msg.addresses:
            host, port, id = peer
            self.factory.connect_to(id, host, port)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash((self.id, self.client, self.address))
