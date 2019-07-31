"""
author: ADG

"""

from .transaction import Transaction
from .wallet import Wallet


class TransactionPool(list):
    """Represents a transaction pool."""

    def add_transaction(self, trans):
        """Add the given transaction `trans` to this transaction pool.
        Returns true if the transaction is considered valid and was successfully added.
        Returns false otherwise."""
        try:
            assert Wallet.verify_transaction(trans) == True
            assert trans.index not in [tx.index for tx in self]
            self.append(trans)
            self.sort(key=lambda tx: tx.qty)
            return True
        except:
            return False

    def pull_transaction(self):
        """Pop and return a transaction from this transaction pool.
        Returns None if the transaction pool is empty."""
        try:
            return self.pop()
        except IndexError:
            return None

    def import_transactions(self, block):
        """Insert all the transactions in the given block to this transaction pool.
        Returns True if successful.
        Note that if this returns False, then only some of the transactions
        may have been added to this transaction pool."""
        for node in block.trans_tree.walk(block.trans_tree.root):
            if type(node._data) == Transaction:
                if self.add_transaction(node._data) == False:
                    return False
        return True

    def remove_transaction(self, tx):
        """Remove the given transaction from this transaction pool."""
        for t in self:
            if t.index == tx.index:
                self.remove(t)
