#!/usr/bin/env python3

import logging
import os
import queue
from glob import glob

from model.transaction import Transaction
from model.wallet import Wallet
from twisted.internet.task import LoopingCall

logger = logging.getLogger(__name__)


class WebWallet(object):
    """Represents a wallet, usable within the explorer web app."""

    def __init__(self):
        self.wallet_name = None
        self.wallets = {}
        self.taskq = queue.Queue()

        # load wallets from disk
        self.load_wallets()

        self.looping_call = LoopingCall(self.miner_tick)
        tick_seconds = 1
        self.looping_call.start(tick_seconds)

    def is_mining(self):
        """Returns True if mining is in progress. False otherwise."""
        return self.taskq.qsize() > 0

    def mine(self, block):
        """Compute proof of work."""
        i = 0
        print(f"target: {block.target}")
        print(f"block initial proof: {block.proof}")
        while True:
            proof = str(i)
            if block.validate_proof(proof=proof):
                block.proof = proof
                return block
            i += 1

    def miner_tick(self):
        """Check whether any mining tasks were added, and if so
        get them from the task queue and execute them."""
        while True:
            try:
                wallet, p2p = self.taskq.get(block=False, timeout=1)
                magic = p2p.bc.magic
                coinbase = Transaction("0", wallet.get_address(), 1, magic=magic)
                wallet.sign_transaction(coinbase)

                b = p2p.bc.new_block(tx=coinbase)
                self.mine(b)
                success = p2p.bc.discard_block(b)
                if success:
                    p2p.broadcast_block(b)
                    logger.debug("Successfully mined and broadcasted block.")
                else:
                    logger.debug("Failed to discard block.")
            except queue.Empty:
                break

    def wallet_names(self):
        """Returns a list of names of generated wallets"""
        return self.wallets.keys()

    def load_wallets(self):
        """Load existing wallets from disk."""
        count = 0
        for path in glob("webwallet_*.wallet"):
            w = Wallet.load_keys(path)
            self.wallets[path] = w
            count += 1
        logging.debug(f"Successfully loaded {count} wallets from disk")

    def generate_wallet(self):
        """Generate a new wallet."""
        w = Wallet()
        w.create_keys()
        first_free_count = 1
        while True:
            path = f"webwallet_{first_free_count}.wallet"
            if not os.path.exists(path):
                break
            first_free_count += 1

        # save wallet to disk
        w.save_key(path)

        # save wallet to memory
        self.wallets[path] = w

        return path

    def set_active_wallet(self, wallet_name):
        """Set the wallet with name `wallet_name` as the active wallet."""
        if wallet_name in self.wallets:
            self.wallet_name = wallet_name
            return True
        return False

    def active_wallet(self):
        """Returns the name of the active wallet."""
        return self.wallet_name

    def get_active_wallet(self):
        """Returns the active wallet or None if there is no active wallet."""
        return self.wallets.get(self.wallet_name, None)

    def send_tx(self, destination, quantity, p2p):
        """Perform a transaction."""
        w = self.get_active_wallet()
        magic = p2p.bc.magic
        tx = Transaction(w.get_address(), destination, quantity, magic=magic)
        w.sign_transaction(tx)

        success = p2p.bc.add_transaction(tx)
        if success:
            # broadcast transaction to p2p network
            p2p.broadcast_tx(tx)
            return True
        else:
            logging.debug("Failed to add transaction.")
            return False

    def start_mining(self, p2p):
        """Start mining a block (add task to queue)."""
        wallet = self.get_active_wallet()
        self.taskq.put((wallet, p2p))
