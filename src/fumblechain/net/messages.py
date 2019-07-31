"""
author: ADG

Represent all messages

References:
    * https://en.bitcoin.it/wiki/Protocol_documentation
    * https://bitcoin.org/en/p2p-network-guide
"""

import json
import logging

from model.block import Block
from model.transaction import Transaction

logger = logging.getLogger(__name__)


class SerializationError(Exception):
    pass


class DeserializationError(Exception):
    pass


class Msg:
    """Base class for all message types."""
    COMMAND = "unknown"

    def __init__(self):
        pass

    def serialize(self, **kwargs):
        """serialize this message"""
        raise NotImplementedError

    def deserialize(self, data):
        """deserialize this message"""
        raise NotImplementedError

    def __str__(self):
        return '\"{}\" message'.format(self.COMMAND.upper())


class MsgVersion(Msg):
    COMMAND = "version"
    PORT = "port"

    def serialize(self, port=0):
        return dict(command=MsgVersion.COMMAND, port=port)

    def deserialize(self, data):
        self.data = data
        self.port = data["port"]


class MsgVerack(Msg):
    COMMAND = "verack"

    def serialize(self, **kwargs):
        return MsgVerack.COMMAND

    def deserialize(self, data):
        self.data = data


class MsgPing(Msg):
    COMMAND = "ping"

    def serialize(self, **kwargs):
        return self.COMMAND

    def deserialize(self, data):
        self.data = data


class MsgPong(Msg):
    COMMAND = "pong"

    def serialize(self, **kwargs):
        return self.COMMAND

    def deserialize(self, data):
        self.data = data


class MsgGetaddr(Msg):
    COMMAND = "getaddr"

    def serialize(self, **kwargs):
        return self.COMMAND

    def deserialize(self, data):
        self.data = data


class MsgAddr(Msg):
    COMMAND = "addr"
    NB = "count"
    ADDRESSES = "addresses"

    def serialize(self, peers=None):
        logger.debug("sending peers: {}".format(peers))
        if not peers:
            raise SerializationError("bad or no peers")
        addresses = [peer.address + (peer.id,) for peer in peers]
        return {self.NB: len(addresses),
                self.ADDRESSES: addresses}

    def deserialize(self, data):
        nb = data[self.NB]
        addresses = data[self.ADDRESSES]
        if nb != len(addresses):
            logger.error("bad number of peers")
            raise DeserializationError("bad number of peers")
        self.addresses = addresses


class MsgGetblocks(Msg):
    COMMAND = "getblocks"
    BHASH = "topblockhash"

    def serialize(self, topblockhash=None):
        logger.debug("top block hash: {}".format(topblockhash))
        if not topblockhash:
            raise SerializationError("bad topblockhash")
        return {self.BHASH: topblockhash}

    def deserialize(self, data):
        self.topblockhash = data[self.BHASH]


class MsgInv(Msg):
    COMMAND = "inv"
    NB = "count"
    OBJECTS = "objects"
    # types of entry
    TYPE_BLOCK = "block"
    TYPE_TX = "tx"
    TYPES = [TYPE_BLOCK, TYPE_TX]

    def serialize(self, objects=[], otype=None):
        logger.debug("objects of type {}: {}".format(otype, objects))
        if not isinstance(objects, list) or not otype:
            raise SerializationError("bad object or no type")
        if otype not in MsgInv.TYPES:
            raise SerializationError("bad object type")
        entries = [(otype, obj) for obj in objects]
        return {self.NB: len(entries),
                self.OBJECTS: entries}

    def deserialize(self, data):
        nb = data[self.NB]
        objs = data[self.OBJECTS]
        if nb != len(objs):
            logger.error("bad number of objects")
            raise DeserializationError("bad number of objects")
        self.objects = []
        for ot in objs:
            otype = ot[0]
            obj = ot[1]
            if otype == MsgInv.TYPE_BLOCK:
                obj = Block.from_json(json.dumps(obj))
            elif otype == MsgInv.TYPE_TX:
                obj = Transaction.from_json(json.dumps(obj))
            self.objects.append((otype, obj))


class MsgBlock(Msg):
    COMMAND = "block"

    def serialize(self, block):
        return block

    def deserialize(self, data):
        b = Block.from_json(json.dumps(data))
        self.block = b


class MsgTx(Msg):
    COMMAND = "tx"

    def serialize(self, tx):
        return tx

    def deserialize(self, data):
        tx = Transaction.from_json(json.dumps(data))
        self.tx = tx


class MsgReject(Msg):
    COMMAND = "reject"
    BHASH = "block_hash"

    def serialize(self, block_hash=None):
        logger.debug("block hash: {}".format(block_hash))
        if not block_hash:
            raise SerializationError("bad block_hash")
        return {self.BHASH: block_hash}

    def deserialize(self, data):
        self.block_hash = data[self.BHASH]


MESSAGE_TYPES = [MsgVersion,
                 MsgVerack,
                 MsgPing,
                 MsgPong,
                 MsgAddr,
                 MsgGetaddr,
                 MsgGetblocks,
                 MsgInv,
                 MsgBlock,
                 MsgTx,
                 MsgReject]
