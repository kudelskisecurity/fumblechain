#!/usr/bin/env python3

"""FumbleChain test suite."""

import datetime
import json
import logging
import math
import os
import shutil
import tempfile
import unittest
from os import path

from api.api import app
from model.block import Block
from model.blockchain import BlockChain
from model.transaction import Transaction
from model.transactionpool import TransactionPool
from model.tree import Tree
from model.treenode import TreeNode
from model.wallet import Wallet

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOGLEVEL", logging.INFO))


def mine(b):
    """Compute proof of work."""
    i = 0
    while (1):
        if b.validate_proof(str(i)):
            b.proof = str(i)
            return str(i)
        i += 1


class WalletHelper:
    """Helper methods to build new transactions and wallets."""

    @staticmethod
    def enrich_wallet_coinbase(cls):
        w = Wallet()
        w.create_keys()
        tx = Transaction("0", w.get_address(), 1)  # coinbase
        w.sign_transaction(tx)

        cls.w = w
        cls.tx = tx

        return w, tx

    @staticmethod
    def generate_wallet_and_coinbase():
        w = Wallet()
        w.create_keys()
        tx = Transaction("0", w.get_address(), 1)  # coinbase
        w.sign_transaction(tx)

        return w, tx

    @staticmethod
    def generate_coinbase_with_unused_wallet():
        tx = Transaction("0", "foobar", 1)
        return tx


class SerializationTest(unittest.TestCase):
    """Tests related to serialization/deseralization."""

    def setUp(self):
        WalletHelper.enrich_wallet_coinbase(self)

    def test_serialize(self):
        a = Block(0, 1, datetime.datetime.utcnow().timestamp())
        b = Block.from_json(a.to_json())
        self.assertEqual(a.get_hash(), b.get_hash())

    def test_block_serialize(self):
        a = Block(0, 1, datetime.datetime.utcnow().timestamp())
        t1 = Transaction(0, 1, 2)
        a.add_transaction(t1)
        t2 = Transaction(0, 1, 2)
        a.add_transaction(t2)

        b = Block.from_json(a.to_json())
        self.assertEqual(a.get_hash(), b.get_hash())

    def test_transaction_serialize(self):
        t1 = Transaction(0, 1, 2)
        t2 = Transaction(0, 1, 2)

        self.assertNotEqual(t1.get_hash(), t2.get_hash())

        t3 = Transaction.from_json(t1.to_json())
        self.assertEqual(t1.get_hash(), t3.get_hash())
        self.assertEqual(t1.src, t3.src)
        self.assertEqual(t1.dst, t3.dst)
        self.assertEqual(t1.qty, t3.qty)

        w = Wallet()
        w.create_keys()
        w.sign_transaction(t1)
        t4 = Transaction.from_json(t1.to_json())
        self.assertEqual(t1.get_hash(), t4.get_hash())

    def test_blockchain_serialize(self):
        bc = BlockChain()

        b = bc.new_block(self.tx)
        mine(b)
        self.assertTrue(bc.discard_block(b))

        bc2 = BlockChain.from_json(bc.to_json())
        self.assertEqual(bc.get_block_from_index(-1).get_hash(), bc2.get_block_from_index(-1).get_hash())
        self.assertEqual(bc.get_block_from_index(0).get_hash(), bc2.get_block_from_index(0).get_hash())

    def test_tree_serialize(self):
        t = Tree()
        u = Tree.from_json(t.to_json())

        self.assertEqual(t.root.get_hash(), u.root.get_hash())

        trans1 = Transaction(0, 1, 2)
        self.assertTrue(t.add_transaction(trans1))
        trans2 = Transaction(1, 2, 3)
        self.assertTrue(t.add_transaction(trans2))
        trans3 = Transaction(2, 3, 4)
        self.assertTrue(t.add_transaction(trans3))

        u = Tree.from_json(t.to_json())
        self.assertEqual(t.root._child_1.get_hash(), u.root._child_1.get_hash())
        self.assertEqual(t.root.get_hash(), u.root.get_hash())


class TreeTest(unittest.TestCase):
    """Tests related to MerkleTree implementation."""

    def test_create_tree(self):
        t = Tree()
        self.assertEqual(t.depth, 0)

        self.assertEqual(len(list(Tree.walk(t.root))), 1)

    def test_nodes(self):
        n = TreeNode()
        self.assertEqual(len(n.children), 2)
        self.assertEqual(n.children[0], None)
        self.assertEqual(n.children[1], None)

        n1 = TreeNode()
        self.assertTrue(n.add_child(n1))

        n2 = TreeNode()
        self.assertTrue(n.add_child(n2))
        self.assertEqual(n.children[0], n1)
        self.assertEqual(n.children[1], n2)

        n3 = TreeNode()
        self.assertFalse(n.add_child(n3))

    def test_transaction(self):
        """One tree node can contain only one transaction"""
        n = TreeNode()
        t = Transaction(0, 1, 1)
        self.assertTrue(n.add_child(t))

        n1 = TreeNode()
        self.assertFalse(n.add_child(n1))

    def test_add_transactions(self):
        t = Tree()
        trans1 = Transaction(0, 1, 2)
        self.assertTrue(t.add_transaction(trans1))
        self.assertEqual(t.depth, 0)

        trans2 = Transaction(1, 2, 3)
        self.assertTrue(t.add_transaction(trans2))
        self.assertEqual(t.depth, 1)

        trans3 = Transaction(2, 3, 4)
        self.assertTrue(t.add_transaction(trans3))
        self.assertEqual(t.depth, 2)

        trans4 = Transaction(3, 4, 5)
        self.assertTrue(t.add_transaction(trans4))
        self.assertEqual(t.depth, 2)

        self.assertEqual(len(list(Tree.walk(t.root))), 7)

        expected_remaining_transactions_before_failure = 2 ** Tree.MAX_DEPTH - 4

        for i in range(expected_remaining_transactions_before_failure):
            tx = Transaction(0, 0, 1)
            t.add_transaction(tx)

        # Cannot add a fifth transaction, since the MAX_DEPTH equals to 2
        trans5 = Transaction(4, 5, 6)
        self.assertFalse(t.add_transaction(trans5))
        self.assertEqual(t.depth, Tree.MAX_DEPTH)

    def test_locate_transaction(self):
        t = Tree()
        trans1 = Transaction(0, 1, 2)
        self.assertTrue(t.add_transaction(trans1))

        trans2 = Transaction(1, 2, 3)
        self.assertTrue(t.add_transaction(trans2))
        self.assertEqual(t.depth, 1)

        self.assertTrue(t.is_present(trans1))

        trans3 = Transaction(0, 1, 2)
        self.assertFalse(t.is_present(trans3))


class BlockTest(unittest.TestCase):
    """Tests related to Block class."""

    def setUp(self):
        WalletHelper.enrich_wallet_coinbase(self)

    def test_create_block(self):
        b = Block(0, 0, 0)
        self.assertIsInstance(b, Block)

        t = Transaction(0, 1, 2)

        self.assertTrue(b.add_transaction(t))

        header = b.get_header()
        header = json.loads(header)
        self.assertIsInstance(header, dict)
        self.assertIsInstance(header["trans_tree"], str)

    def test_block_mine(self):
        for i in range(1, 5):
            b = Block(0, 0, 0)
            mine(b)
            self.assertTrue(b.validate_proof())

    def test_walk_transactions(self):
        b = Block(0, 0, 0)
        t = Transaction(0, 1, 2)
        b.add_transaction(t)
        self.assertEqual(len(list(b.get_transactions())), 1)
        t = Transaction(0, 1, 2)
        b.add_transaction(t)
        self.assertEqual(len(list(b.get_transactions())), 2)
        for x in b.get_transactions():
            self.assertIsInstance(x, Transaction)


class BlockChainTest(unittest.TestCase):
    """Tests related to BlockChain class."""

    def setUp(self):
        WalletHelper.enrich_wallet_coinbase(self)

    def test_create_chain(self):
        bc = BlockChain()
        self.assertIsInstance(bc.new_block(), Block)
        self.assertEqual(len(bc.chain), 1)

        self.assertFalse(bc.get_block_from_index(1337))

        # Cannot add block when previous has not been proven
        b = bc.new_block()
        self.assertFalse(bc.discard_block(b))

    def test_add_block(self):
        bc = BlockChain()

        # Can add block when previous has been proven
        b = bc.new_block(self.tx)
        mine(b)
        self.assertTrue(bc.discard_block(b))

        self.assertTrue(bc.get_block_from_index(1).validate_proof())
        self.assertEqual(bc.get_block_from_index(0).index, 0)
        self.assertEqual(len(bc.chain), 2)
        self.assertNotEqual(bc.get_block_from_index(0).get_hash(), bc.get_block_from_index(-1).get_hash())

    def test_discard_block(self):
        bc = BlockChain()

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b = bc.new_block(cbtx)
        mine(b)
        self.assertTrue(bc.discard_block(b))

        b = Block(1337, bc.get_block_from_index(1).get_hash())
        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b.add_transaction(cbtx)
        mine(b)
        self.assertFalse(bc.discard_block(b))
        self.assertEqual(len(bc.chain), 2)

        b = Block(bc.get_block_from_index(-1).index, "obviously_fake_hash")
        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b.add_transaction(cbtx)
        mine(b)
        self.assertFalse(bc.discard_block(b))
        self.assertEqual(len(bc.chain), 2)

        b = Block(bc.get_block_from_index(1).index + 1, bc.get_block_from_index(1).get_hash())
        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b.add_transaction(cbtx)  # coinbase
        mine(b)
        self.assertTrue(bc.discard_block(b))
        self.assertEqual(len(bc.chain), 3)

    def test_block_chaining(self):
        bc = BlockChain()
        for i in range(5):
            cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
            b = bc.new_block(cbtx)
            mine(b)
            self.assertTrue(bc.discard_block(b))

        self.assertEqual(len(bc.chain), 6)
        for i in range(6):
            self.assertEqual(bc.get_block_from_index(i).index, i)
        for i in range(1, 6):
            self.assertEqual(bc.get_block_from_index(i - 1).get_hash(), bc.get_block_from_index(i).prevhash)

    def test_search_block(self):
        bc = BlockChain()
        for i in range(5):
            cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
            b = bc.new_block(cbtx)
            mine(b)
            self.assertTrue(bc.discard_block(b))

        for i in range(6):
            h = bc.get_block_from_index(i).get_hash()
            self.assertEqual(bc.get_block_from_hash(h), bc.get_block_from_index(i))

        self.assertFalse(bc.get_block_from_hash("abc"))

    def test_file_save(self):
        test_dir = tempfile.mkdtemp()
        test_file = path.join(test_dir, "blockchain.json")

        bc = BlockChain()
        b = bc.new_block(self.tx)
        mine(b)
        bc.discard_block(b)
        self.assertTrue(bc.save_to_file(test_file))
        self.assertIsInstance(BlockChain.load_from_file(test_file), BlockChain)

        shutil.rmtree(test_dir)

    def test_block_since(self):
        bc = BlockChain()

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b = bc.new_block(cbtx)
        mine(b)
        bc.discard_block(b)

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b2 = bc.new_block(cbtx)
        mine(b2)
        bc.discard_block(b2)

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b3 = bc.new_block(cbtx)

        self.assertEqual(len(bc.get_blocks_since(b.get_hash())), 1)
        self.assertEqual(len(bc.get_blocks_since(b2.get_hash())), 0)

        # Block b3 is not in the blockchain
        self.assertIsNone(bc.get_blocks_since(b3.get_hash()))

    def test_wallet_balance(self):
        bc = BlockChain()

        w1 = Wallet()
        w1.create_keys()
        addr1 = w1.get_address()

        w2 = Wallet()
        w2.create_keys()
        addr2 = w2.get_address()

        w3 = Wallet()
        w3.create_keys()
        addr3 = w3.get_address()

        tx0 = Transaction("0", addr1, 1)
        b = bc.new_block(tx0)
        mine(b)
        bc.discard_block(b)

        balance = bc.get_wallet_balance(addr1)
        self.assertEqual(balance, 1)

        tx1 = Transaction(addr1, addr2, 0.1)
        tx2 = Transaction(addr1, addr3, 0.2)
        tx3 = Transaction(addr2, addr3, 133)

        w1.sign_transaction(tx1)
        w1.sign_transaction(tx2)
        w2.sign_transaction(tx3)

        self.assertTrue(bc.add_transaction(tx1))
        self.assertTrue(bc.add_transaction(tx2))
        self.assertFalse(bc.add_transaction(tx3))

        tx4 = Transaction(addr1, addr2, 1)
        w1.sign_transaction(tx4)
        self.assertFalse(bc.add_transaction(tx4))

        balance = bc.get_wallet_balance(addr1)
        self.assertEqual(balance, 0.7)

        balance = bc.get_wallet_balance(addr2)
        self.assertEqual(balance, 0.1)

        balance = bc.get_wallet_balance(addr3)
        self.assertEqual(balance, 0.2)

        w4 = Wallet()
        w4.create_keys()
        addr4 = w4.get_address()

        cbtx4 = Transaction("0", addr4, 1)
        b4 = bc.new_block(cbtx4)
        mine(b4)
        bc.discard_block(b4)
        self.assertTrue(bc.get_wallet_balance(addr4), 1)

        ntx4 = Transaction(addr4, "toto", 1, magic=bc.magic)
        w4.sign_transaction(ntx4)
        self.assertTrue(bc.add_transaction(ntx4))
        coinbase4 = Transaction("0", addr4, 1)
        nb4 = bc.new_block(coinbase4)  # new block nb4 is filled with coinbase4 and ntx4 (fill_block() was called)
        mine(nb4)  # mine block before adding to chain
        logger.debug("DISCARDING...")
        discarded = bc.discard_block(nb4)
        logger.debug("END DISCARD")
        self.assertTrue(discarded)

    def test_inf_nan_balance(self):
        bc = BlockChain()

        tx = Transaction("src", "dst", math.inf)

        is_found = False
        balance, is_found = bc.update_balance("src", math.inf, tx, is_found)
        self.assertEqual(is_found, True)
        self.assertEqual(balance, math.inf)

    def test_secure_wallet_balance(self):
        bc = BlockChain()

        w1 = Wallet()
        w1.create_keys()
        addr1 = w1.get_address()

        tx0 = Transaction("0", addr1, 1)
        b = bc.new_block(tx0)
        mine(b)
        bc.discard_block(b)

        balance = bc.get_secure_wallet_balance(addr1)
        self.assertEqual(balance, None)

        tx1 = Transaction(addr1, "toto", 1)
        w1.sign_transaction(tx1)

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b1 = bc.new_block(cbtx)
        b1.add_transaction(tx1)
        mine(b1)
        bc.discard_block(b1)

        self.assertEqual(bc.get_secure_wallet_balance("toto"), None)

        for i in range(5):
            tx0 = Transaction("0", addr1, 1)
            b = bc.new_block(tx0)
            mine(b)
            bc.discard_block(b)

        # only 5 confirmations so far, tx is not there yet for secure balance
        self.assertEqual(bc.get_secure_wallet_balance("toto"), None)

        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b6 = bc.new_block(cbtx)
        mine(b6)
        bc.discard_block(b6)

        # tx appears after 6 confirmations only
        self.assertEqual(bc.get_secure_wallet_balance("toto"), 1)

    def test_same_chain_replay_fix(self):
        bc = BlockChain()

        w, cbtx = WalletHelper.generate_wallet_and_coinbase()

        b = bc.new_block(cbtx)
        mine(b)
        self.assertTrue(bc.discard_block(b))

        b2 = bc.new_block(cbtx)  # reuse cbtx on purpose
        mine(b2)
        self.assertFalse(bc.discard_block(b2))


class WalletTest(unittest.TestCase):
    def test_sign_and_verify(self):
        t = Wallet()
        t.create_keys()
        sig = t.sign(bytes.fromhex("d8e8fca2dc0f896fd7cb4cb0031ba249"))
        res = t.verify(sig, bytes.fromhex("d8e8fca2dc0f896fd7cb4cb0031ba249"))

        self.assertTrue(res)

    def test_save_and_load_key(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.test_file = path.join(self.test_dir, "test.pem")

        t = Wallet()
        t.create_keys()
        t.save_key(self.test_file)
        t2 = Wallet.load_keys(self.test_file)

        self.assertIsNotNone(t.get_address())
        self.assertIsNotNone(t2.get_address())
        self.assertEqual(t2.get_address(), t.get_address())

        shutil.rmtree(self.test_dir)

    def test_sign_transaction(self):
        w = Wallet()
        w.create_keys()

        t = Transaction(w.get_address(), 1, 1)
        th = t.get_hash()

        self.assertIsNone(t.signature)

        self.assertTrue(w.sign_transaction(t))

        self.assertIsNotNone(t.signature)
        self.assertEqual(t.get_hash(), th)

        self.assertTrue(w.verify_transaction(t))

    def test_verify_foreign_transaction(self):
        w = Wallet()
        w.create_keys()
        t = Transaction(w.get_address(), 1, 1)
        w.sign_transaction(t)

        # Create different keypair
        w.create_keys()

        self.assertTrue(w.verify_transaction(t))


class TransactionPoolTest(unittest.TestCase):
    """Tests related to TransactionPool implementation."""

    def setUp(self):
        WalletHelper.enrich_wallet_coinbase(self)

    def test_pool(self):
        tp = TransactionPool()
        self.assertEqual(len(tp), 0)

        t = Transaction(0, 1, 1)
        self.assertFalse(tp.add_transaction(t))

    def test_add_transactions(self):
        tp = TransactionPool()
        w = Wallet()
        w.create_keys()

        t = Transaction(w.get_address(), 1, 1)
        # Transaction is not signed
        self.assertFalse(tp.add_transaction(t))

        w.sign_transaction(t)
        self.assertTrue(tp.add_transaction(t))

        # Canot add the same transaciton multiple times
        self.assertFalse(tp.add_transaction(t))

        self.assertEqual(len(tp), 1)

        t2 = tp.pull_transaction()
        self.assertEqual(t.get_hash(), t2.get_hash())

    def test_import_transactions(self):
        b = Block(0, 0)
        w = Wallet()
        w.create_keys()
        t = Transaction(w.get_address(), 1, 1)
        w.sign_transaction(t)
        b.add_transaction(t)

        tp = TransactionPool()
        self.assertTrue(tp.import_transactions(b))
        self.assertEqual(len(tp), 1)

        t2 = tp.pull_transaction()
        self.assertEqual(t.get_hash(), t2.get_hash())

        # Importing unsigned transactions returns False
        tp = TransactionPool()
        t2 = Transaction(0, 1, 1)
        b.add_transaction(t2)
        self.assertFalse(tp.import_transactions(b))

    def test_use_pool(self):
        bc = BlockChain()
        w = Wallet()
        w.create_keys()

        # make some cash
        tx0 = Transaction("0", w.get_address(), 1)
        b = bc.new_block(tx0)
        mine(b)
        self.assertTrue(bc.discard_block(b))

        self.assertEqual(bc.get_wallet_balance(w.get_address()), 1)
        tx_count = 10
        for i in range(tx_count):
            t = Transaction(w.get_address(), 1, 1 / 100)
            w.sign_transaction(t)
            self.assertTrue(bc.add_transaction(t))
        self.assertEqual(len(bc.transaction_pool), tx_count)
        b = bc.new_block(self.tx)

        max_txs_in_block = 2 ** Tree.MAX_DEPTH
        self.assertEqual(len(list(b.get_transactions())), min(max_txs_in_block, tx_count + 1))

        # Transactions in new block are removed from tx pool when new block is successfully discarded to chain
        b = bc.new_block(self.tx)  # coinbase tx
        mine(b)
        bc.discard_block(b)

        expected_txs_in_tx_pool = max(0, tx_count - (max_txs_in_block - 1))
        self.assertEqual(len(bc.transaction_pool), expected_txs_in_tx_pool)

        leftover_count = min(max_txs_in_block - 1, expected_txs_in_tx_pool)
        self.assertEqual(len(list(bc.new_block(self.tx).get_transactions())), 1 + leftover_count)


class ClientAPITest(unittest.TestCase):
    """Tests related to the client REST API."""

    def setUp(self):
        WalletHelper.enrich_wallet_coinbase(self)

    class DummyP2p():

        def broadcast_block(self, block):
            pass

        def broadcast_tx(self, tx):
            pass

    def test_post_transaction(self):
        self.prepare_app()

        # prepare a valid transaction
        w = Wallet()
        w.create_keys()
        tx = Transaction("0", w.get_address(), 1)
        w.sign_transaction(tx)

        client = app.test_client()

        response = client.post("/block/new", data=tx.to_json())
        self.assertEqual(response.status_code, 201)

        b = Block.from_json(response.get_data())
        mine(b)
        response = client.post("/block", data=b.to_json())
        self.assertEqual(response.status_code, 201)

        tx = Transaction(w.get_address(), 1, 0.5)

        # test without signature
        response = client.post("/transaction", data=tx.to_json())
        self.assertEqual(response.status_code, 400)

        # test with signature
        w.sign_transaction(tx)
        response = client.post("/transaction", data=tx.to_json())
        self.assertEqual(response.status_code, 201)

    def test_post_new_block(self):
        self.prepare_app()

        # prepare a valid transaction
        w = Wallet()
        w.create_keys()
        tx = Transaction(0, w.get_address(), 1)
        w.sign_transaction(tx)

        client = app.test_client()

        response = client.post("/block/new", data=tx.to_json())
        self.assertEqual(response.status_code, 201)

        b = Block.from_json(response.get_data())
        self.assertTrue(type(b) == Block)

    def test_post_block(self):
        p2p = ClientAPITest.DummyP2p()
        bc = BlockChain()
        p2p.bc = bc
        app.p2p = p2p

        # make some cash first
        w, cbtx = WalletHelper.generate_wallet_and_coinbase()
        cash_block = bc.new_block(cbtx)
        mine(cash_block)
        bc.discard_block(cash_block)

        txs = []
        for i in range(4):
            tx = Transaction(w.get_address(), i, 0.1)
            w.sign_transaction(tx)
            txs.append(tx)

        # mine current block
        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        current_block = bc.new_block(cbtx)
        mine(current_block)
        # put current block in chain and create new block
        bc.discard_block(current_block)

        # create new block
        cbtx = WalletHelper.generate_coinbase_with_unused_wallet()
        b = bc.new_block(cbtx)
        for tx in txs:
            b.add_transaction(tx)

        client = app.test_client()

        # POST new UN-mined block (should fail and return 400 bad request)
        response = client.post("/block", data=b.to_json())
        self.assertEqual(response.status_code, 400)

        # mine new block
        mine(b)

        # POST new mined block (should work this time)
        response = client.post("/block", data=b.to_json())
        self.assertEqual(response.status_code, 201)

    def prepare_app(self):
        # setup app.p2p.bc
        p2p = ClientAPITest.DummyP2p()
        bc = BlockChain()
        p2p.bc = bc
        app.p2p = p2p


if __name__ == "__main__":
    unittest.main()
