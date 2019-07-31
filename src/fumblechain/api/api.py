#!/usr/bin/env python3

"""FumbleChain client REST API implementation."""

import logging
import sys
import traceback

from flask import Flask
from flask import Response
from flask import jsonify
from flask import request
from werkzeug.exceptions import NotFound, BadRequest

from model.block import Block
from model.transaction import Transaction

app = Flask(__name__)

logger = logging.getLogger(__name__)

HTTP_CREATED = 201


@app.route("/peers", methods=["GET"])
def get_peers():
    """Returns the list of connected peers."""
    peers = []
    for peer in app.p2p.factory.nodes.values():
        peers.append(peer.to_json())

    response = {
        "peers": peers
    }

    return jsonify(response)


@app.route("/transaction_pool", methods=["GET"])
def get_transaction_pool():
    """Returns the list of transactions currently in the transaction pool."""
    txs = [x.serialize() for x in app.p2p.bc.transaction_pool]

    response = {
        "transactions": txs
    }

    return jsonify(response)


@app.route("/transaction/<tx_id>", methods=["GET"])
def get_transaction(tx_id):
    """Returns the transaction with given id `tx_id`.
    Returns HTTP 404 if no such transaction exists."""
    tx = app.p2p.bc.get_transaction(tx_id)
    if tx is not None:
        return tx.to_json()
    else:
        raise NotFound()


@app.route("/blockchain", methods=["GET"])
def get_blockchain():
    """Returns the complete blockchain in JSON format."""
    bc = app.p2p.bc
    return bc.to_json()


@app.route("/block/<block_id>", methods=["GET"])
def get_block(block_id):
    """Returns the block with given id `block_id`.
    Returns HTTP 404 if no such block exists.
    Returns HTTP 400 if the block ID is not an ID."""
    try:
        b = app.p2p.bc.get_block_from_index(int(block_id))
        if b != False:
            return b.to_json()
        else:
            raise NotFound()
    except ValueError:
        raise BadRequest()


@app.route("/wallet/<address>/balance", methods=["GET"])
def get_wallet_balance(address):
    """Returns the balance for the wallet with given address `address`.
    Returns HTTP 404 if no such wallet can be found."""
    balance = app.p2p.bc.get_wallet_balance(address)

    if balance is not None:
        response = {
            "address": address,
            "balance": balance
        }

        return jsonify(response)
    else:
        raise NotFound()


@app.route("/wallet/<address>/secure_balance", methods=["GET"])
def get_secure_wallet_balance(address):
    """Returns the *secure* balance (includes only transactions with at least 6 confirmations)
    for the wallet with given address `address`.
    Returns HTTP 404 if no such wallet can be found."""
    balance = app.p2p.bc.get_secure_wallet_balance(address)

    if balance is not None:
        response = {
            "address": address,
            "balance": balance
        }

        return jsonify(response)
    else:
        raise NotFound()


@app.route("/transaction", methods=["POST"])
def create_transaction():
    """Add and broadcast the given transaction.
    Returns HTTP 400 if the transaction is considered invalid."""
    try:
        # retrieve transaction from request body
        jso = request.get_data(as_text=True)
        tx = Transaction.from_json(jso)

        # add transaction to local blockchain
        success = app.p2p.bc.add_transaction(tx)
        if success:
            # broadcast transaction to p2p network
            app.p2p.broadcast_tx(tx)

            return Response(tx.to_json(), status=HTTP_CREATED)
        else:
            logger.debug("failed to add tx")
            raise BadRequest()
    except BadRequest:
        raise
    except BaseException as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        logger.debug(sys.exc_info())
        raise BadRequest()


@app.route("/block/new", methods=["POST"])
def post_new_block():
    """Create and return a new block, ready for mining."""
    try:
        # retrieve transaction from request body
        jso = request.get_data(as_text=True)
        tx = Transaction.from_json(jso)

        # generate new block
        b = app.p2p.bc.new_block(tx)
        return Response(b.to_json(), status=HTTP_CREATED)
    except BaseException as e:
        logger.debug(e)
        logger.debug(traceback.format_exc())
        logger.debug(sys.exc_info())
        raise


@app.route("/block", methods=["POST"])
def create_block():
    """Add and broadcast the given block.
    Returns HTTP 400 if the block is considered invalid."""
    try:
        # retrieve block from request body
        jso = request.get_data(as_text=True)
        b = Block.from_json(jso)

        # add block to local blockchain
        success = app.p2p.bc.discard_block(b)

        if success:
            # broadcast block to p2p network
            app.p2p.broadcast_block(b)

            logger.debug(f"block {b.index} added")
            return Response(b.to_json(), status=HTTP_CREATED)
        else:
            logger.debug("failed to add block (discard)")
            raise BadRequest()
    except BadRequest:
        raise
    except BaseException as e:
        logger.debug(e)
        raise BadRequest()


@app.route("/magic", methods=["GET"])
def get_magic():
    """Returns this blockchain's magic value."""
    magic = app.p2p.bc.magic
    response = {
        "magic": magic
    }
    return jsonify(response)
