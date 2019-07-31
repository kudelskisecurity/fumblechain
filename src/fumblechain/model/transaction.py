"""
author: ADG

Represent a transaction
"""
import json
import uuid
from hashlib import md5 as HASH_ALG

from utils.serde import Encoder


class Transaction:
    """Represents a transaction."""

    def __init__(self, src, dst, qty, magic=0xdeadbeef, index=None, signature=None, *args, **kwargs):
        if index is None:
            self.index = str(uuid.uuid4())
        else:
            self.index = index
        self.src = src
        self.dst = dst
        self.qty = qty
        self.signature = signature
        self.magic = magic

    @staticmethod
    def from_json(data):
        """Loads a JSON representation, and returns an object"""
        try:
            dic = json.loads(data)
            b = Transaction(**dic)
            return b
        except:
            raise (ValueError("JSON could not be loaded"))

    def to_json(self):
        """Returns a JSON representation of our object"""
        return json.dumps(self, sort_keys=True, cls=Encoder)

    def get_hash(self):
        """Returns the hash of this transaction."""
        data = dict(self._serialize())
        data.pop("signature")
        data = json.dumps(data, sort_keys=True)
        return HASH_ALG(data.encode()).hexdigest()

    def _serialize(self):
        data = self.__dict__
        return data

    def serialize(self):
        return self._serialize()

    def add_signature(self, sig):
        """Appends the given signature `sig` to this transaction.
        Returns True if this transaction has not already been signed.
        Returns False otherwise.
        """
        if self.signature is None:
            self.signature = sig
            return True
        else:
            return False
