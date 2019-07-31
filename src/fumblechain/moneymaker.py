#!/usr/bin/env python3

"""Challenge 1 moneymaker service"""

import os

from flask import Flask
from flask import render_template
from flask import request
from werkzeug.exceptions import BadRequest

from cli import API
from model.transaction import Transaction
from model.wallet import Wallet

# local node url
CLIENT_API_HOST = os.environ["CHALLENGE1_MONEYMAKER_CLIENT_API_HOST"]
# wallet filepath
MONEYMAKER_WALLET_PATH = os.environ["CHALLENGE1_MONEYMAKER_WALLET_PATH"]
# how many FumbleCoins to send per request
TX_AMOUNT = float(os.environ["CHALLENGE1_MONEYMAKER_TX_AMOUNT"])

app = Flask(__name__)

app.wallet = Wallet.load_keys(MONEYMAKER_WALLET_PATH)


@app.route("/")
def root():
    """Display FumbleCoin request form."""
    return render_template("request_cash.html", tx_amount=TX_AMOUNT)


@app.route("/cash", methods=["POST"])
def post_cash():
    """Send coins and display confirmation message"""
    try:
        requester_wallet_address = request.form["destination"]

        # send coins to requester wallet address
        send_cash(requester_wallet_address, TX_AMOUNT)

        return render_template("send_confirmation.html", tx_amount=TX_AMOUNT, address=requester_wallet_address)
    except KeyError:
        print("Destination address is missing")
        raise BadRequest()


def send_cash(destination, amount):
    """Send `amount` FumbleCoins to wallet with address `destination`."""
    source = app.wallet.get_address()
    tx = Transaction(source, destination, amount)
    print(f"sending tx of {amount} from:")
    print(source)
    print("to:")
    print(destination)
    app.wallet.sign_transaction(tx)

    api = API(CLIENT_API_HOST)
    success = api.push_transaction(tx)
    return success


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=os.environ["CH1_MONEYMAKER_PORT"])
