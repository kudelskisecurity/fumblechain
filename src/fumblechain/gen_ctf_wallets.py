#!/usr/bin/env python3

"""Generate CTF wallets used for the challenges"""

import os

from model.wallet import Wallet
from utils import gen_common_factor_keys
from utils import genkey

CHALLENGE_WALLETS_FILENAME_PREFIX = "ctf_wallet_addresses"
ENV_VAR_NAME = "CTF_WALLET_ADDRESSES"
VOLUME_PATH = "gen/"


def write_echoservice_env(ch3_wallet):
    """Write env file for challenge 3's echo service"""
    with open(f"{VOLUME_PATH}echoservice.env", "w+") as fout:
        addr = ch3_wallet.get_address()
        print(f"CHALLENGE3_ECHOSERVICE_WALLET_ADDRESS={addr}", file=fout)


def write_files(pubkeys, challenge_string):
    """Write both bash (export) and env files"""
    write_bash_file(pubkeys, f"{VOLUME_PATH}{CHALLENGE_WALLETS_FILENAME_PREFIX}_{challenge_string}.bash")
    write_env_file(pubkeys, f"{VOLUME_PATH}{CHALLENGE_WALLETS_FILENAME_PREFIX}_{challenge_string}.env")


def write_env_file(pubkeys, destination):
    """Write env file located at `destination` for given `pubkeys`."""
    with open(destination, "w+") as fout:
        env_value = ",".join(pubkeys)
        print(f"{ENV_VAR_NAME}={env_value}", end="", file=fout)


def write_bash_file(pubkeys, destination):
    """Same as `write_env_file()` except that it contains the `export` bash directive
    so that the file can be sourced.
    """
    with open(destination, "w+") as fout:
        env_value = ",".join(pubkeys)
        print(f"export {ENV_VAR_NAME}={env_value}", end="", file=fout)


def generate_or_load_random_wallet(wallet, wallet_dir):
    """Load or generate wallet located at `wallet_dir`/`wallet`.
    If it does not exist, generate a new random wallet.
    If it already exists, load the existing wallet.
    Return the wallet (either loaded or generated) in both cases.
    """
    destination = f"{wallet_dir}/{wallet}"
    if not os.path.exists(destination):
        privkey = genkey.genkey()
        w = Wallet.load_keys_from_bytes(privkey.encode("utf-8"))

        with open(destination, "w+") as fout:
            print(privkey, end="", file=fout)
    else:
        w = Wallet.load_keys(destination)

    return w


def generate_challenge1_wallets(wallet_dir):
    """Generate wallets for challenge 1"""
    # generate random wallet
    ch1_pubkeys = []
    ch1_wallet = generate_or_load_random_wallet("moneymaker.wallet", wallet_dir)
    ch1_pubkeys.append(ch1_wallet.get_address())
    write_files(ch1_pubkeys, "ch1")
    return ch1_pubkeys


def generate_challenge2_wallets(wallet_dir):
    """Generate wallets for challenge 2"""
    # generate RSA common factor wallets for challenge 2
    ch2_pubkeys = []
    w1, w2 = gen_common_factor_keys.gen_common_factor_wallets()
    wallet_targets = [
        (w1, "ch2a.wallet"),
        (w2, "ch2b.wallet")
    ]
    for wallet, filename in wallet_targets:
        destination = f"{wallet_dir}/{filename}"
        if not os.path.exists(destination):
            wallet.save_key(destination)
        else:
            wallet = Wallet.load_keys(destination)

        ch2_pubkeys.append(wallet.get_address())
    write_files(ch2_pubkeys, "ch2")
    return ch2_pubkeys


def generate_challenge3_wallets(wallet_dir):
    """Generate wallets for challenge 3"""
    # generate the echoservice wallet
    ch3_pubkeys = []
    ch3_wallet = generate_or_load_random_wallet("echoservice.wallet", wallet_dir)
    ch3_pubkeys.append(ch3_wallet.get_address())
    write_files(ch3_pubkeys, "ch3")
    write_echoservice_env(ch3_wallet)
    return ch3_pubkeys


def main():
    wallet_dir = f"{VOLUME_PATH}wallets"
    os.makedirs(wallet_dir, exist_ok=True)

    ch1_pubkeys = generate_challenge1_wallets(wallet_dir)
    ch2_pubkeys = generate_challenge2_wallets(wallet_dir)
    ch3_pubkeys = generate_challenge3_wallets(wallet_dir)

    # write all addresses .bash file for fumblestore .tar.gz client
    pubkeys = ch1_pubkeys + ch2_pubkeys + ch3_pubkeys
    write_bash_file(pubkeys, f"{VOLUME_PATH}{CHALLENGE_WALLETS_FILENAME_PREFIX}.bash")


if __name__ == '__main__':
    main()
