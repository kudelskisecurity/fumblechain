"""
author: ADG

Represent a block in the blockchain
"""

import datetime
import json
import logging
from hashlib import md5 as HASH_ALG

from model import transaction, tree
from utils.serde import Encoder

logger = logging.getLogger(__name__)


class Block(object):
    """Represents a block in the chain."""

    def __init__(
            self, index, prevhash, timestamp=None, trans_tree=None, proof="", target=0xffffffffffffffffffffffffffffff):
        self.index = index
        self.prevhash = prevhash
        if timestamp is None:
            self.timestamp = datetime.datetime.utcnow().timestamp()
        else:
            self.timestamp = timestamp
        if trans_tree is None:
            self.trans_tree = tree.Tree()
        else:
            self.trans_tree = trans_tree
        self.proof = proof
        self.target = target

    def get_transaction(self, tx_id):
        """Returns the transaction with given uuid `tx_id` if it exists in this block.
        Returns None otherwise."""
        # for tx in self.transactions:
        for tx in self.get_transactions():
            try:
                if tx.index == tx_id:
                    return tx
            except:
                pass

        return None

    def get_hash(self, proof=""):
        """Generates the hash of the curent block"""
        if self.proof != "":
            proof = self.proof
        data = self.get_header()
        data += proof
        h = HASH_ALG(data.encode("utf-8"))
        return int.from_bytes(h.digest(), byteorder="little")

    def validate_proof(self, proof="", debug=False):
        """Validates that the given proof (nonce) is valid for the current block"""
        h = self.get_hash(proof)
        if debug:
            logger.debug(f"h: {h}")
            logger.debug(f"target: {self.target}")
        return h < self.target

    @staticmethod
    def from_json(data):
        """Loads a JSON representation, and returns an object"""
        try:
            if type(data) != dict:
                dic = json.loads(data)
            else:
                dic = data
            dic["trans_tree"] = tree.Tree.from_json(json.dumps(dic["trans_tree"]))
            b = Block(**dic)
            return b
        except:
            raise (ValueError("JSON could not be loaded"))

    def to_json(self):
        """Returns a JSON representation of our object"""
        return json.dumps(self, sort_keys=True, cls=Encoder)

    def add_transaction(self, tx):
        """Add the given transaction to the current block."""
        try:
            assert type(tx) == transaction.Transaction
            return self.trans_tree.add_transaction(tx)
        except:
            return False

    def _serialize(self):
        data = self.__dict__
        return data

    def get_header(self):
        """Returns the block header in JSON format"""
        data = {
            "index": self.index,
            "prevhash": self.prevhash,
            "trans_tree": self.trans_tree.root.get_hash(),
            "timestamp": self.timestamp,
            "target": self.target,
        }
        return json.dumps(data, sort_keys=True)

    def get_transactions(self):
        """Successively yield transactions in this block.
        Note that this is a generator and must therefore be iterated over."""
        for node in tree.Tree.walk(self.trans_tree.root):
            if type(node._data) == transaction.Transaction:
                yield node._data

    def clear_tree(self):
        """Deletes the current transaction tree and create an empty one"""
        if self.proof == "":
            del (self.trans_tree)
            self.trans_tree = tree.Tree()
            return True
        else:
            return False
