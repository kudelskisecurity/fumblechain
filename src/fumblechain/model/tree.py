"""
author: NOB

"""

import json

from utils.serde import Encoder
from .treenode import TreeNode


class Tree(object):
    """Represents a Merkle tree."""

    MAX_DEPTH = 8

    def __init__(self, root=None, depth=0, max_depth=MAX_DEPTH):
        if root is None:
            self.root = TreeNode()
        else:
            self.root = root
        self.depth = depth
        self.max_depth = max_depth

    def _add_root(self):
        """Add a new root to the tree, and create the new node branch."""
        if self.depth < self.max_depth:
            new_root = TreeNode()
            self.root.add_parent(new_root)
            self.root = new_root

            self.root.add_child(Tree._add_branch(self.depth))
            self.depth += 1
        else:
            raise (ValueError("Max tree depth reached"))

    def add_transaction(self, tx):
        """Add the given transaction to this tree.
        Returns True if successful and False otherwise."""
        for node in Tree.walk(self.root):
            if node.add_child(tx) == True:
                return True
        if self.depth < self.max_depth:
            self._add_root()
            return self.add_transaction(tx)
        else:
            return False

    @staticmethod
    def _add_branch(depth):
        if depth > 0:
            n = TreeNode()
            n.add_child(Tree._add_branch(depth - 1))
            n.add_child(Tree._add_branch(depth - 1))
            return n
        else:
            return TreeNode()

    @staticmethod
    def walk(node):
        """Walk this tree and recursively yield nodes (transactions).
        In practice, we store transactions in each node."""
        if node is None:
            return
        else:
            for child in node.children:
                yield from Tree.walk(child)
            yield node

    @staticmethod
    def print(node, depth=0):
        """Print this tree starting from given node."""
        if node is None:
            return
        else:
            if node._data is not None:
                print(
                    "T "
                    + " " * depth
                    + str(node.get_hash() + " ->" + str(node._data.get_hash()))
                )
            else:
                print("N " + " " * depth + str(node.get_hash()))
            for child in node.children:
                Tree.print(child, depth + 1)

    @staticmethod
    def from_json(data):
        """Loads a JSON representation, and returns an object"""
        try:
            dic = json.loads(data)
            root = TreeNode.from_json(dic["root"])
            dic.update({"root": root})
            t = Tree(**dic)
            return t
        except:
            raise (ValueError("JSON could not be loaded"))

    def to_json(self):
        """Returns a JSON representation of our object"""
        return json.dumps(self, sort_keys=True, cls=Encoder)

    def _serialize(self):
        data = self.__dict__
        return data

    def is_present(self, trans):
        """Returns True if the transaciton is part of this tree"""
        for node in Tree.walk(self.root):
            try:
                if node._data.get_hash() == trans.get_hash():
                    return True
            except:
                pass
        return False
