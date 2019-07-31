#!/usr/bin/env python3

"""Generate a new wallet and print it"""

from model.wallet import Wallet


def genkey():
    w = Wallet()
    w.create_keys()
    pkey = w.get_private_key()
    output = pkey.decode("utf-8")
    return output


def main():
    output = genkey()
    print(output, end="")


if __name__ == '__main__':
    main()
