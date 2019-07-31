#!/usr/bin/env python3

import datetime
import json
import logging
import os
import textwrap

from flask import Flask
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from werkzeug.exceptions import NotFound

from explorer.webwallet import WebWallet

template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "explorer")
app = Flask(__name__, template_folder=template_folder)
app.debug = True

FLASH_SUCCESS = "success"
FLASH_ERROR = "error"
FLASH_INFO = "info"

logger = logging.getLogger(__name__)

app.secret_key = os.urandom(32)

# webwallet state
WEBWALLET = WebWallet()


def printable_block(b):
    """Build block structure with printable fields only."""
    txs = list(b.get_transactions())
    tx_count = len(txs)
    coinbase = txs[0] if len(txs) > 0 else None

    blk = {
        "index": b.index,
        "target": hex(b.target),
        "hash": hex(b.get_hash()),
        "prevhash": hex(b.prevhash) if b.prevhash != 0 else None,
        "timestamp": b.timestamp,
        "proof": b.proof,
        "txs": txs,
        "tx_count": tx_count,
        "miner": coinbase.dst if coinbase is not None else coinbase,
        "size_bytes": len(b.to_json())
    }
    return blk


def get_transaction_count():
    """Returns the total number of transactions in the chain."""
    tx_count = 0
    for b in app.p2p.bc.chain:
        tx_count += len(list(b.get_transactions()))
    return tx_count


def get_latest_blocks(max_blocks=5):
    """Returns the latest X blocks in the chain."""
    bc = app.p2p.bc

    blocks = []
    count = 0
    for b in bc.chain[::-1]:
        blk = printable_block(b)
        blocks.append(blk)
        count += 1

        if count >= max_blocks:
            break

    return blocks


def get_latest_transactions(max_txs=10):
    """Returns the latest X transactions in the chain."""
    bc = app.p2p.bc

    latest_txs = []
    count = 0
    for b in bc.chain[::-1]:
        txs = list(b.get_transactions())
        for tx in txs[::-1]:
            latest_txs.append(tx)
            count += 1
            if count >= max_txs:
                return latest_txs

    return latest_txs


################################################
# Template filters
################################################

@app.template_filter("datetime")
def datetime_filter(date):
    """Flask template filter to pretty print datetimes."""
    return datetime.datetime.fromtimestamp(date).isoformat()


@app.template_filter("wrap")
def textwrap_filter(text, width=80):
    """Flask template filter to wrap lines to X characters (X=80 by default)."""
    return "<br />".join(textwrap.wrap(text, width))


@app.template_filter("address")
def address(addr):
    """Make wallet addresses more easily distinguishable.
    All addresses start and end with the same string.
    Print some characters in the middle instead.
    """
    if len(addr) >= 90:
        return addr[90:90 + 32]
    else:
        return addr


################################################
# Endpoints
################################################

@app.route("/", methods=["GET"])
def get_home():
    """Display FumbleChain explorer home page - endpoint"""
    bc = app.p2p.bc
    p2p = app.p2p

    blocks_count = len(bc.chain)
    tx_count = get_transaction_count()
    peers = p2p.factory.nodes
    peers_count = len(peers)
    blocks = get_latest_blocks()
    txs = get_latest_transactions()
    target = hex(bc.target)

    return render_template("home.html", blocks=blocks, blocks_count=blocks_count, txs=txs, tx_count=tx_count, bc=bc,
                           p2p=app.p2p, target=target,
                           peers_count=peers_count)


@app.route("/block/<int:block_id>")
def get_block(block_id):
    """Show block with id `block_id` - endpoint."""
    try:
        b = app.p2p.bc.chain[block_id]
        blk = printable_block(b)

        return render_template("block.html", b=blk)
    except IndexError:
        raise NotFound()


@app.route("/tx/<tx_id>")
def get_tx(tx_id):
    """Show transaction with id `tx_id` - endpoint."""
    tx = app.p2p.bc.get_transaction(tx_id)
    if tx is not None:
        pretty_json = json.dumps(json.loads(tx.to_json()), indent=4, sort_keys=True)
        return render_template("transaction.html", tx=tx, pretty_json=pretty_json)
    else:
        raise NotFound()


@app.route("/wallet/<wallet_address>")
def get_wallet(wallet_address):
    """Show wallet with address `wallet_address` - endpoint."""
    balance = app.p2p.bc.get_wallet_balance(wallet_address)
    txs, ins, outs = app.p2p.bc.get_wallet_transactions(wallet_address)
    max_txs = 500  # maximum number of incoming or outgoing transactions to display (each) on the wallet page
    return render_template("wallet.html", balance=balance, addr=wallet_address, txs=txs, ins=ins[:max_txs],
                           outs=outs[:max_txs])


@app.route("/peers")
def get_peers():
    """Show connected peers - endpoint."""
    peers = app.p2p.factory.nodes.values()
    peer_count = len(peers)
    return render_template("peers.html", peers=peers, peer_count=peer_count)


@app.route("/txpool")
def get_tx_pool():
    """Show transaction pool - endpoint."""
    txs = app.p2p.bc.transaction_pool
    tx_count = len(txs)
    return render_template("txpool.html", txs=txs, tx_count=tx_count)


@app.route("/webwallet")
def get_webwallet():
    """WebWallet - endpoint."""
    balance = None
    address = None
    wallet = WEBWALLET.get_active_wallet()

    if wallet is not None:
        address = wallet.get_address()
        balance = app.p2p.bc.get_wallet_balance(address)

    return render_template("webwallet.html", webwallet=WEBWALLET, balance=balance, address=address)


@app.route("/webwallet/generate", methods=["POST"])
def post_webwallet_generate():
    """Create a new wallet - endpoint."""
    WEBWALLET.generate_wallet()
    return redirect("/webwallet")


@app.route("/webwallet/select", methods=["POST"])
def post_webwallet_select_wallet():
    """Select wallet - endpoint"""
    wallet = request.form["wallet"]
    WEBWALLET.set_active_wallet(wallet)
    return redirect("/webwallet")


@app.route("/webwallet/tx", methods=["POST"])
def post_webwallet_tx_send():
    """Send transaction - endpoint"""
    destination = request.form["destination"]
    try:
        quantity = float(request.form["quantity"])
    except ValueError:
        flash(f"Invalid transaction quantity.", FLASH_ERROR)
        return redirect("/webwallet")

    success = WEBWALLET.send_tx(destination, quantity, app.p2p)

    if success:
        flash(f"Successfully broadcasted transaction of {quantity} FumbleCoins.", FLASH_SUCCESS)
    else:
        flash(f"Failed to broadcast transaction.", FLASH_ERROR)

    return redirect("/webwallet")


@app.route("/webwallet/mine/toggle", methods=["POST"])
def post_webwallet_mine_toggle():
    """Start mining a block - endpoint"""
    WEBWALLET.start_mining(app.p2p)
    return redirect("/webwallet")
