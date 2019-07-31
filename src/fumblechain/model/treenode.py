import json
from hashlib import md5 as HASH_ALG

from model import transaction
from utils.serde import Encoder


class TreeNode:
    """Represents a Merkle tree node."""

    def __init__(self, _child_1=None, _child_2=None, _data=None):
        self._child_1 = _child_1
        self._child_2 = _child_2
        self._data = _data

    def add_parent(self, parent):
        return parent.add_child(self)

    def add_child(self, data):
        """Add a child to the node. Returns True if OK, False if the node is full"""
        if type(data) == TreeNode and self._data is None:
            if self._child_1 is None:
                self._child_1 = data
                return True
            elif self._child_2 is None:
                self._child_2 = data
                return True
            else:
                return False
        else:
            if self.is_empty:
                self._data = data
                return True
            else:
                return False

    def get_hash(self):
        """Returns the hash of this node."""
        if self._data is not None:
            return HASH_ALG(str(self._data.to_json()).encode()).hexdigest()
        else:
            try:
                to_hash = ""
                to_hash += self._child_1.get_hash()
                to_hash += self._child_2.get_hash()
            except:
                pass
            finally:
                return HASH_ALG(to_hash.encode()).hexdigest()

    @property
    def is_empty(self):
        """Returns True if this node is empty.
        False otherwise.
        """
        if self._child_1 is None and self._child_2 is None and self._data is None:
            return True
        else:
            return False

    @property
    def children(self):
        """Returns the list of children of this node.
        A node containing data has an empty list of children."""
        if self._data is None:
            return [self._child_1, self._child_2]
        else:
            return []

    def show(self):
        print(repr(self))

    @staticmethod
    def from_json(data):
        """Loads a JSON representation, and returns an object"""
        try:
            if type(data) != dict:
                dic = json.loads(data)
            else:
                dic = data
            if dic["_child_1"] is not None:
                c1 = TreeNode.from_json(dic["_child_1"])
                dic.update({"_child_1": c1})
            if dic["_child_2"] is not None:
                c2 = TreeNode.from_json(dic["_child_2"])
                dic.update({"_child_2": c2})
            if dic["_data"] is not None:
                t = transaction.Transaction(**dic["_data"])
                dic.update({"_data": t})
            n = TreeNode(**dic)
            return n
        except:
            raise (ValueError("JSON could not be loaded"))

    def to_json(self):
        """Returns a JSON representation of our object"""
        return json.dumps(self, sort_keys=True, cls=Encoder)

    def _serialize(self):
        data = self.__dict__
        return data
