"""
author: ADG

"""

import json
import logging
import math
import os

from utils.serde import Encoder
from .block import Block
from .transaction import Transaction
from .transactionpool import TransactionPool
from .wallet import Wallet

logger = logging.getLogger(__name__)


class BlockChain:
    """Represents a chain of blocks."""
    _base_target = 0xffffffffffffffffffffffffffffff
    MAX_TARGET = 2 ** 126
    TARGET_WINDOW_SIZE_IN_BLOCKS = 10
    BLOCK_INTERVAL_SECONDS = 6

    def __init__(self, chain=None, magic=0xdeadbeef, *args, **kwargs):
        if chain is None:
            self.chain = list()
            # Usually, the genesis block goes here
            self.chain.append(Block(0, 0))
        else:
            self.chain = chain
        self.transaction_pool = TransactionPool()
        self.magic = magic

    def get_wallet_transactions(self, address):
        """Returns all the transactions involving the given address.
        Actually returns 3 values:
          * txs: all the transactions
          * ins: incoming transactions
          * outs: outgoing transactions
        """
        txs = []
        ins = []
        outs = []
        current_balance = 0
        if address == "0" or address in self.get_ctf_wallet_addresses():
            current_balance = math.inf

        for b in self.chain:
            for tx in b.get_transactions():

                if tx.src == address or tx.dst == address:
                    balance_before = current_balance
                    if tx.src == address:
                        current_balance -= tx.qty

                    if tx.dst == address:
                        current_balance += tx.qty

                    t = (tx, b.timestamp, b.index, balance_before, current_balance)
                    txs.insert(0, t)

                    if tx.src == address:
                        outs.insert(0, t)
                    if tx.dst == address:
                        ins.insert(0, t)

        return txs, ins, outs

    def get_wallet_balance(self, address):
        """Returns the balance for the given wallet address.
        Returns None if the wallet address does not exist."""
        if address == "0" or address in self.get_ctf_wallet_addresses():
            return math.inf
        balance = 0
        is_found = False
        for b in self.chain:
            for tx in b.get_transactions():
                # add or remove funds to balance
                balance, is_found = self.update_balance(address, balance, tx, is_found)
        # also process txs in tx pool
        for tx in self.transaction_pool:
            balance, is_found = self.update_balance(address, balance, tx, is_found)

        if is_found:
            return balance
        else:
            return None

    def get_secure_wallet_balance(self, address):
        """Returns the (secure) balance for the given wallet address.
                Returns None if the wallet address does not exist.
        The balance is considered secure after 6 confirmations.
        """
        if address == "0" or address in self.get_ctf_wallet_addresses():
            return math.inf
        balance = 0
        is_found = False
        for b in self.chain[:-6]:  # 6 confirmations
            for tx in b.get_transactions():
                # add or remove funds to balance
                balance, is_found = self.update_balance(address, balance, tx, is_found)

        # explicitly do not count transactions not in confirmed blocks (in transaction pool)
        pass

        if is_found:
            return balance
        else:
            return None

    def update_balance(self, address, balance, tx, is_found):
        """Helper function for get_(secure_)wallet_balance().
        Updates the wallet balance and returns it as well as whether
        the balance was updated with the given transaction.
        """
        if tx.src == address:
            if not math.isinf(balance):  # prevent balance from becoming "nan"
                balance -= tx.qty
            is_found = True
        elif tx.dst == address:
            if not math.isinf(balance):  # prevent balance from becoming "nan"
                balance += tx.qty
            is_found = True

        return balance, is_found

    def get_ctf_wallet_addresses(self):
        """Returns the list of addresses with infinite coins.
        These addresses are considered to have infinite FumbleCoins.
        This feature is useful for implementing CTF challenges in the FumbleStore.
        """
        env_var_name = "CTF_WALLET_ADDRESSES"
        if env_var_name in os.environ:
            return os.environ[env_var_name].split(",")
        else:
            return []

    def get_transaction(self, tx_id):
        """Returns the transaction with given uuid `tx_id` if it exists in any block of this blockchain.
        Returns None otherwise."""
        for block in self.chain:
            tx = block.get_transaction(tx_id)
            if tx is not None:
                return tx
        return None

    def add_transaction(self, trans):
        """Adds a transaction to the blockchain.
        This actually puts the transaction to the transaction pool until it is added to a mined block."""

        # only allow positive quantity transactions
        if math.isnan(trans.qty) or trans.qty <= 0:
            return False

        try:
            assert self.get_wallet_balance(trans.src) >= trans.qty
            assert self.transaction_pool.add_transaction(trans) == True
            logger.debug("tx added to tx pool")
            return True
        except TypeError:
            return False
        except AssertionError:
            return False

    def get_block_from_index(self, index):
        """Returns the block with the given index.
        The special index "-1" can be used to obtain the latest block.
        Returns False if no block with such an index exists in the current chain."""
        if index == -1:
            return self.chain[-1]
        for b in self.chain:
            if b.index == index:
                return b
        return False

    def get_block_from_hash(self, block_hash):
        """Returns the block with the given hash.
        Returns None if no such block exists in the current chain."""
        for b in self.chain:
            if b.get_hash() == block_hash:
                return b
        return None

    def get_blocks_since(self, block_hash):
        """Get a list of all blocks added to the chain after the block with given `block_hash`.
        Returns a list of blocks.
        Returns an empty list if the given block hash corresponds to the current latest block.
        Returns None if no block with the given hash exists in the current chain."""
        block = self.get_block_from_hash(block_hash)

        if block in self.chain:
            return self.chain[self.chain.index(block) + 1:]
        else:
            return None

    @property
    def target(self):
        """Calculates the current target difficulty
        The following diagram explains when the target is re-computed.

        --------------------------------------------------------------------> Time
        [0]-[1]-[2]-[3]-[4]-[5]-[6]-[7]-[8]-[9]-[ ]-[ ]-[ ]-[ ]-[ ]-[ ]-[16]-[ ]- - - - -
         |                               |                               |
         -> Initial                      -> Target changes               -> Target is again re-computed
            target (genesis block)          every X blocks (here X=8)       starting from here
                                                                            for the next X blocks (included)
        """
        top_block = self.get_block_from_index(-1)
        height = top_block.index + 1
        if height < BlockChain.TARGET_WINDOW_SIZE_IN_BLOCKS:
            return self._base_target

        target = top_block.target

        if height % BlockChain.TARGET_WINDOW_SIZE_IN_BLOCKS != 0:
            return target
        else:
            # target needs to be corrected
            logger.debug("Next block is getting a corrected target!")
            start = height - BlockChain.TARGET_WINDOW_SIZE_IN_BLOCKS
            end = height
            window = self.chain[start:end]
            first = window[0]
            last = window[-1]
            duration = last.timestamp - first.timestamp
            expected_duration = BlockChain.TARGET_WINDOW_SIZE_IN_BLOCKS * BlockChain.BLOCK_INTERVAL_SECONDS
            c = duration
            e = expected_duration
            correction_factor = 1 - ((c - e) / c)  # can only be 0 when e = 0
            previous_target = target
            target /= correction_factor

            # always keep an integer target
            target = int(target)

            # min target is 1
            target = max(1, target)

            if target > BlockChain.MAX_TARGET:
                target = BlockChain.MAX_TARGET
                logger.debug("Clamping target to MAX_TARGET")

            logger.debug(f"Window size: {BlockChain.TARGET_WINDOW_SIZE_IN_BLOCKS}")
            logger.debug(f"Block interval seconds: {BlockChain.BLOCK_INTERVAL_SECONDS}")
            logger.debug(f"Previous target: {previous_target}")
            logger.debug(f"Current duration: {c}")
            logger.debug(f"Expected duration: {e}")
            logger.debug(f"Correction factor: {correction_factor}")
            logger.debug(f"New target: {target}")
            return target

    def discard_block(self, new_block):
        """Add a new block to the chain.
        Performs all sanity checks before adding the block
        This function is also able to replace the top block in the following conditions :
            - The smallest timestamp wins (the block was mined first)
            - The smallest difficulty wins

        Returns True if the block was added, False otherwise."""
        is_valid_block = self.is_valid_block(new_block)
        if not is_valid_block:
            logger.debug("Block is not considered valid")
            return False

        top_block = self.get_block_from_index(-1)

        # If we have a concurrency problem
        if new_block.index == top_block.index:
            if new_block.timestamp > top_block.timestamp:
                return False
            if new_block.get_hash() > top_block.get_hash():
                return False
            self.pop_block()

        # check that no transaction is replayed
        is_tx_replay_free = self.is_block_txs_replay_free(new_block)
        if not is_tx_replay_free:
            logger.debug("Block has transactions that have been replayed")
            return False

        is_txs_positive = self.is_block_txs_positive(new_block)
        if not is_txs_positive:
            logger.debug("Block has negative of NaN transaction quantities")
            return False

        is_txs_balanced = self.is_block_txs_balanced(new_block)
        if not is_txs_balanced:
            logger.debug("Block has transactions where wallet balance is negative")
            return False
        else:
            for tx in new_block.get_transactions():
                self.transaction_pool.remove_transaction(tx)

        self.chain.append(new_block)
        return True

    def new_block(self, tx=None):
        """Create and return a new block with the given coinbase transaction `tx`
        ready for being mined.
        """
        top_block = self.get_block_from_index(-1)
        b = Block(top_block.index + 1, top_block.get_hash(), target=self.target)

        if not self.is_valid_coinbase_transaction(tx):
            logger.debug("invalid transaction (new block)")

        try:
            assert b.add_transaction(tx) == True
        except:
            pass
        finally:
            self._fill_block(b)
        return b

    def is_valid_coinbase_transaction(self, tx):
        """Returns true if the given transaction `tx` is a valid coinbase transaction.
        Returns False otherwise.
        """
        if type(tx) != Transaction:
            logger.debug("coinbase: type(tx) != Transaction")
            return False
        if tx is None:
            logger.debug("coinbase: tx is None")
            return False
        if tx.src != "0":
            logger.debug("coinbase: tx.src != 0")
            return False
        if tx.qty != 1:
            logger.debug("coinbase: tx.qty != 1")
            return False

        return True

    def is_block_txs_positive(self, block):
        """Returns true if all transactions in the given block have a positive and non-NaN quantity.
        Returns False otherwise."""
        for tx in block.get_transactions():
            if math.isnan(tx.qty) or tx.qty <= 0:
                return False
        return True

    def is_block_txs_balanced(self, block):
        """Returns true if all transactions in the given block lead to no negative balances.
        Returns False otherwise.
        """
        balances = {}
        seen_txs = set()
        for tx in self.transaction_pool:
            seen_txs.add(tx.index)

        for tx in block.get_transactions():
            # check that we do not count txs twice
            if tx.index in seen_txs:
                continue
            seen_txs.add(tx.index)

            # check that no transaction leads to negative wallet balance
            src = tx.src
            if src not in balances:
                balances[src] = self.get_wallet_balance(src)
            if balances[src] is None:
                return False
            balances[src] -= tx.qty

            if balances[src] < 0:
                return False

        return True

    def is_block_txs_replay_free(self, new_block):
        # build a set with all tx.index in the new block
        new_block_tx_indexes = set()
        for tx in new_block.get_transactions():
            new_block_tx_indexes.add(tx.index)

        # iterate over all txs in the current blockchain and return False is there is any duplicate
        for b in self.chain:
            for tx in b.get_transactions():
                if tx.index in new_block_tx_indexes:
                    return False

        return True

    def is_valid_block(self, block):
        """Returns true if the given block is considered valid.
        Returns False otherwise.
        """
        top_block = self.get_block_from_index(-1)
        if block.validate_proof() == False:
            logger.debug("block.validate_proof() == False")
            block.validate_proof(debug=True)
            return False
        if block.prevhash != top_block.get_hash():
            logger.debug("block.prevhash != top_block.get_hash()")
            return False
        if block.index != (top_block.index) + 1:
            logger.debug("block.index != top_block.index + 1")
            return False
        if block.target != self.target:  # target should match
            logger.debug("block.target != self.target")
            return False

        transactions = list(block.get_transactions())
        coinbase_tx = transactions[0]
        if not self.is_valid_coinbase_transaction(coinbase_tx):
            logger.debug("coinbase is invalid")
            return False

        # check transaction signatures
        for i, tx in enumerate(transactions):
            # check all tx signatures except for the coinbase tx (checked above)
            if i > 0 and not Wallet.verify_transaction(tx):
                logger.debug(f"Invalid signature for transaction in block. tx.index={tx.index}")
                return False

        return True

    def pop_block(self):
        """Removes the top block from the chain"""
        self.chain.pop()

    def _serialize(self):
        data = dict(self.__dict__)
        data.pop("transaction_pool")
        return data

    @staticmethod
    def from_json(data):
        """Loads a JSON representation, and returns an object"""
        try:
            if type(data) != dict:
                dic = json.loads(data)
            else:
                dic = data
            dic["chain"] = [Block.from_json(b) for b in dic["chain"]]
            b = BlockChain(**dic)
            return b
        except:
            raise (ValueError("JSON could not be loaded"))

    def to_json(self):
        """Returns a JSON representation of our object"""
        return json.dumps(self, sort_keys=True, cls=Encoder)

    def _fill_block(self, blk):
        for t in self.transaction_pool:
            if blk.add_transaction(t) == False:
                break

    def save_to_file(self, path):
        """Save the blockchain in JSON format to the file located at given `path`.
        """
        try:
            with open(path, "w+") as f:
                f.write(self.to_json())
            return True
        except:
            return False

    @staticmethod
    def load_from_file(path):
        """Returns a BlockChain deserialized from the JSON data
        contained in the file located at given `path`.
        """
        try:
            with open(path, "r") as f:
                data = f.read()
            return BlockChain.from_json(data)
        except Exception as e:
            raise e
