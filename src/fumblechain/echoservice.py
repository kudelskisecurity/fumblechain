#!/usr/bin/env python3

"""Challenge 3 echo service"""

import json
import logging
import os
import time

from api.api_wrapper import API
from model.transaction import Transaction
from model.wallet import Wallet

PERSISTENT_DIR = "persistent"
ECHOSERVICE_SLEEP_INTERVAL_SECONDS = int(os.environ.get("CH3_ECHOSERVICE_SLEEP_INTERVAL_SECONDS", default=10))
MIN_CONFIRMATIONS = int(os.environ.get("CH3_ECHOSERVICE_MIN_CONFIRMATIONS", default=1))
ECHOSERVICE_WALLET_PATH = os.environ.get("CH3_ECHOSERVICE_WALLET_PATH", default="wallets/echoservice.wallet")
API_URL = os.environ.get("CH3_MAINNET_API_URL", default="http://localhost:1337")
STATE_KEY = "latest_processed_block_index"

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)


def process_block_with_index(index):
    """Check whether there is any incoming transactions in the block with the given index.
    If so, send an echo transaction back to the sender.
    """
    api = API(API_URL)
    w = Wallet.load_keys(ECHOSERVICE_WALLET_PATH)
    echoservice_addr = w.get_address()
    magic = api.get_magic()

    b = api.get_block(index)
    for tx in b.get_transactions():
        if tx.dst == echoservice_addr:
            logging.info(f"sending echo tx of qty {tx.qty} to {tx.src}")
            # we should send the same amount of coins to that address
            echo_tx = Transaction(echoservice_addr, tx.src, tx.qty, magic=magic)
            w.sign_transaction(echo_tx)
            success = api.push_transaction(echo_tx)
            logging.info(f"done. success: {success}")


def save_state(block_id, state_path):
    """Save the latest processed block's index to disk."""
    payload = {
        STATE_KEY: block_id
    }
    with open(state_path, "w+") as fout:
        json.dump(payload, fout)


def echo(api, latest_processed_block_index, state_path):
    """Process all unprocessed blocks, starting from the block after the one with the index `latest_processed_block_index`.
    Return the index of the latest processed block."""
    # get latest block id
    latest_block_index = api.get_block(-1).index
    latest_confirmed_block_index = latest_block_index - MIN_CONFIRMATIONS

    for index in range(latest_processed_block_index + 1, latest_confirmed_block_index + 1):
        logging.info(f"processing block: {index}")
        process_block_with_index(index)

    latest_processed_block_index = latest_confirmed_block_index
    save_state(latest_processed_block_index, state_path)

    return latest_processed_block_index


def main():
    os.makedirs(PERSISTENT_DIR, exist_ok=True)
    state_path = os.path.join(PERSISTENT_DIR, "echoservice.json")

    # read state from persistent dir
    latest_processed_block_index = 0
    if os.path.exists(state_path):
        with open(state_path) as f:
            latest_processed_block_index = json.load(f)[STATE_KEY]
    else:
        logger.info(f"{state_path} does not exist, creating")
        save_state(latest_processed_block_index, state_path)

    logger.info(f"starting from block {latest_processed_block_index}")

    api = API(API_URL)
    while True:
        try:
            latest_processed_block_index = echo(api, latest_processed_block_index, state_path)
        except BaseException as e:
            logger.info(f"Error while echo(): {e}")
        finally:
            time.sleep(ECHOSERVICE_SLEEP_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
