#!/usr/bin/env bash

# Source addresses of wallets used for the CTF (wallets with infinite coins)
source ctf_wallet_addresses.bash

./daemon.py "$@"