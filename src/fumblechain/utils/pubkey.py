#!/usr/bin/env python3

"""Print the public address of the wallet given on stdin"""

import sys

from model.wallet import Wallet


def pubkey():
    sin = sys.stdin.read().encode("utf-8")
    w = Wallet.load_keys_from_bytes(sin)
    pkey = w.get_address()
    return pkey


def main():
    output = pubkey()
    print(output)


if __name__ == '__main__':
    main()
