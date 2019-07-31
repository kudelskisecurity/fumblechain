#!/usr/bin/env python3

import json

import requests

from model import block
from model import transaction


class API():
    """Wrapper for the FumbleChain client REST API."""

    def __init__(self, api_url):
        """Setup wrapper with the given base API URL."""
        self.api_url = api_url

    def get_block(self, blk_id):
        """Returns the block with id `blk_id`."""
        r = requests.get(f"{self.api_url}/block/{blk_id}")
        if r.status_code != 200:
            return None
        return block.Block.from_json(r.text)

    def new_block(self, tx):
        """Returns a new block with coinbase transaction `tx`, ready for mining."""
        r = requests.post(f"{self.api_url}/block/new", data=tx.to_json())
        if r.status_code != 201:
            return None
        return block.Block.from_json(r.text)

    def push_block(self, blk):
        """Broadcast the given block `blk` and add it to the chain."""
        r = requests.post(f"{self.api_url}/block", data=blk.to_json())
        if r.status_code != 201:
            return False
        else:
            return True

    def get_tx(self, tx_id):
        """Returns the transaction with id `tx_id`."""
        r = requests.get(f"{self.api_url}/transaction/{tx_id}")
        if r.status_code != 200:
            return None
        return transaction.Transaction.from_json(r.text)

    def push_transaction(self, trans):
        """Broadcast the given transaction `trans` and add it to the transaction pool."""
        r = requests.post(f"{self.api_url}/transaction", data=trans.to_json())
        if r.status_code != 201:
            return False
        else:
            return True

    def get_balance(self, address):
        """Returns the balance of the wallet with given address."""
        r = requests.get(f"{self.api_url}/wallet/{address}/balance")
        if r.status_code != 200:
            return None
        return r.json()['balance']

    def get_peers(self):
        """Returns the list of connected peers."""
        r = requests.get(f"{self.api_url}/peers")
        if r.status_code != 200:
            return None
        return r.json()['peers']

    def get_transaction_pool(self):
        """Returns the list of transactions currently in the transaction pool."""
        r = requests.get(f"{self.api_url}/transaction_pool")
        if r.status_code != 200:
            return None
        txs = r.json()["transactions"]
        return [transaction.Transaction.from_json(json.dumps(t)) for t in txs]

    def get_magic(self):
        """Returns the magic value for this blockchain."""
        r = requests.get(f"{self.api_url}/magic")
        if r.status_code != 200:
            return None
        magic = r.json()["magic"]
        return magic
