#!/usr/bin/env python3

"""FumbleChain scriptable CLI client"""

import argparse
import datetime
import sys

from cli import API, show_transaction, show_block
from model import transaction, wallet
from model.block import Block
from model.wallet import Wallet

USER_WALLET = wallet.Wallet()


def mine(tx, api):
    """Compute proof of work."""
    i = 0
    while True:
        b = api.new_block(tx)
        start_time = datetime.datetime.utcnow().timestamp()
        while (datetime.datetime.utcnow().timestamp() - start_time < 30):
            if b.validate_proof(proof=str(i)):
                b.proof = str(i)
                return b
            i += 1


def do_mine(args):
    """Mine a block."""
    w = Wallet.load_keys(args.wallet)
    magic = args.api.get_magic()
    coinbase = transaction.Transaction("0", w.get_address(), 1, magic=magic)

    print("Mining block...")
    b = mine(coinbase, args.api)
    print("Pushing block...")
    args.api.push_block(b)
    print("Successfully mined block.")


def do_transaction(args):
    """Perform a transaction."""
    w = Wallet.load_keys(args.wallet)
    magic = args.api.get_magic()
    tx = transaction.Transaction(w.get_address(), args.destination, args.amount, magic=magic)
    w.sign_transaction(tx)

    if args.api.push_transaction(tx):
        print("Transaction successfully broadcasted.")
    else:
        print("[Error] Failed to broadcast transaction.")


def do_transaction_raw(args):
    """Send raw transaction from JSON input"""
    tx_json = sys.stdin.read()
    try:
        tx = transaction.Transaction.from_json(tx_json)
    except ValueError:
        print("Invalid transaction JSON")
        return

    if args.api.push_transaction(tx):
        print("OK")
    else:
        print("KO")


def do_block_raw(args):
    """Send raw block from JSON input"""
    block_json = sys.stdin.read()
    try:
        blk = Block.from_json(block_json)
    except ValueError:
        print("Invalid block JSON")
        return

    if args.api.push_block(blk):
        print("OK")
    else:
        print("KO")


def do_wallet_generate(args):
    """Generate a new wallet."""
    print("Generating new wallet...")
    w = Wallet()
    w.create_keys()
    w.save_key(args.filepath)
    print(f"New wallet successfully saved at {args.filepath}")


def do_wallet_show(args):
    """Display wallet information."""
    print("Showing wallet")
    w = Wallet.load_keys(args.wallet)

    addr = w.get_address()
    balance = args.api.get_balance(addr)
    print(f"Address: {addr}")
    print(f"Balance: {balance}")


def do_show_block(args):
    """Show block information."""
    bid = args.block_id
    b = args.api.get_block(bid)
    if b is not None:
        show_block(b)
    else:
        print(f"Block with index {bid} does not exist.")


def do_show_transaction(args):
    """Show transaction information."""
    txid = args.transaction_id
    tx = args.api.get_tx(txid)
    if tx is not None:
        show_transaction(tx)
    else:
        print(f"Transaction with id {txid} does not exist.")


def do_show_transaction_json(args):
    """Dump transaction to JSON."""
    txid = args.transaction_id
    tx = args.api.get_tx(txid)
    if tx is not None:
        print(tx.to_json())
    else:
        print(f"Transaction with id {txid} does not exist.")


def do_show_block_json(args):
    """Dump block to JSON."""
    bid = args.block_id
    b = args.api.get_block(bid)
    if b is not None:
        print(b.to_json())
    else:
        print(f"Block with index {bid} does not exist.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FumbleChain non-interactive CLI client")

    def show_help(_):
        parser.print_help()

    parser.set_defaults(func=show_help)
    default_api_url = "http://localhost:1337/"
    parser.add_argument("-H", "--api-url", dest="api_url",
                        help=f"URL to connect to. Default is {default_api_url}.",
                        default=default_api_url)
    parser.add_argument("-w", "--wallet", dest="wallet",
                        help="Path to wallet file to use.",
                        required=True)

    subparsers = parser.add_subparsers()

    transaction_parser = subparsers.add_parser("transaction", aliases=["t", "tx"])
    transaction_parser.set_defaults(func=do_transaction)
    transaction_parser.add_argument("destination", type=str)
    transaction_parser.add_argument("amount", type=float)

    transaction_raw_parser = subparsers.add_parser("transaction_raw", aliases=["traw", "txraw"])
    transaction_raw_parser.set_defaults(func=do_transaction_raw)

    block_raw_parser = subparsers.add_parser("block_raw", aliases=["braw", "blkraw"])
    block_raw_parser.set_defaults(func=do_block_raw)

    mine_parser = subparsers.add_parser("mine", aliases=["m"])
    mine_parser.set_defaults(func=do_mine)

    wallet_parser = subparsers.add_parser("wallet", aliases=["w"])
    wp = wallet_parser.add_subparsers()
    wgenerate = wp.add_parser("generate", aliases=["gen"])
    wgenerate.set_defaults(func=do_wallet_generate)
    wgenerate.add_argument("filepath", type=str)
    wshow = wp.add_parser("show", aliases=["s"])
    wshow.set_defaults(func=do_wallet_show)

    show_parser = subparsers.add_parser("show", aliases=["s"])
    show = show_parser.add_subparsers()
    stx = show.add_parser("transaction", aliases=["t", "tx"])
    stx.set_defaults(func=do_show_transaction)
    stx.add_argument("transaction_id")
    sblock = show.add_parser("block", aliases=["b", "blk"])
    sblock.set_defaults(func=do_show_block)
    sblock.add_argument("block_id")
    stxj = show.add_parser("transaction_json", aliases=["tj", "txj"])
    stxj.set_defaults(func=do_show_transaction_json)
    stxj.add_argument("transaction_id")
    sblockj = show.add_parser("block_json", aliases=["bj", "blkj"])
    sblockj.set_defaults(func=do_show_block_json)
    sblockj.add_argument("block_id")

    args = parser.parse_args()

    API_URL = args.api_url
    print(f"Using API: {API_URL}")
    print(f"Using wallet: {args.wallet}")

    api = API(args.api_url)
    args.api = api

    args.func(args)


if __name__ == '__main__':
    main()
