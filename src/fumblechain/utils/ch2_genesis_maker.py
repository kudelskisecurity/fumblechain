#!/usr/bin/env python3

"""Create transactions for challenge 2"""

import logging
import os
import sys

from model.blockchain import BlockChain
from model.transaction import Transaction
from model.wallet import Wallet

logging.basicConfig(level="DEBUG")


def mine(block):
    i = 0
    while True:
        proof = str(i)
        if block.validate_proof(proof=proof):
            block.proof = proof
            return block
        i += 1


def main():
    # load initial blockchain
    here = os.path.dirname(os.path.abspath(__file__))
    genesis_path = os.path.join(here, "..", "genesis.json")
    with open(genesis_path) as f:
        blockchain_json = f.read()
    bc = BlockChain.from_json(blockchain_json)
    magic = int(os.environ["CHALLENGE2_MAINNET2_MAGIC"])
    bc.magic = magic

    # make transactions from both vulnerable addresses
    dst = "foobar"
    w1path = os.environ["CHALLENGE2_WALLET_A_PATH"]
    w2path = os.environ["CHALLENGE2_WALLET_B_PATH"]
    w1 = Wallet.load_keys(w1path)
    w2 = Wallet.load_keys(w2path)
    tx1 = Transaction(w1.get_address(), dst, 1337, magic=magic)
    tx2 = Transaction(w2.get_address(), dst, 1338, magic=magic)
    coinbase = Transaction("0", w1.get_address(), 1, magic=magic)
    w1.sign_transaction(tx1)
    w2.sign_transaction(tx2)
    b = bc.new_block(coinbase)

    b.add_transaction(tx1)
    b.add_transaction(tx2)
    mine(b)
    success = bc.discard_block(b)
    if not success:
        print("Failed to discard block!")
        sys.exit(-1)

    print(bc.to_json())


if __name__ == '__main__':
    main()
