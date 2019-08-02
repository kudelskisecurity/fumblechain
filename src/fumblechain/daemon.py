#!/usr/bin/env python3

"""
FumbleChain daemon (node)
"""

import logging
import os
import queue

import coloredlogs
from api.api import app as api_app
from docopt import docopt
from explorer.explorer import app as explorer_app
from model.blockchain import BlockChain
from net.address import Address
from net.p2p import P2p

NAME = "daemon"
VERSION = "1.0"
BLOCKCHAIN_PATH = os.environ.get("FUMBLECHAIN_BLOCKCHAIN_PATH", "bc.json")
GENESIS_PATH = "genesis.json"
MAGIC = 0xabcdef12
USAGE = """FumbleChain

Usage:
  {0} start [-l] [-v ...] [--port=<port>] [--peer=<peer>...] [--api-port=<api-port>] [--explorer] [--explorer-port=<explorer-port>] [--magic=<magic>] [--file=<file_path>]
  {0} (-h | --help)
  {0} --version

Options:
  -P --peer=<peer>                  Peer to connect to [default: ].
  -p --port=<port>                  Port to listen on [default: 2222].
  --api-port=<api-port>             Port to listen on for the API [default: 1337].
  --explorer                        Enable blockchain explorer.
  --explorer-port=<explorer-port>   Port to listen on for the explorer [default: 20601].
  --magic=<magic>                   Blockchain magic value [default: 2882400018].
  --file=<file_path>                Path to file containing blockchain data to resume from [default: ].
  -v                                Increase verbosity.
  -h --help                         Show this screen.
  --version                         Show version.
""".format(NAME)


def set_logging(level):
    """Setup logging"""
    level = int(level)
    if level == 0:
        lvl = logging.WARNING
    elif level == 1:
        lvl = logging.INFO
    elif level > 1:
        lvl = logging.DEBUG
    fmt = "%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s"
    coloredlogs.install(level=lvl, fmt=fmt)
    logging.basicConfig(level=lvl, format=fmt)


def main(port, peers=[], api_port=1337, explorer_enabled=False, explorer_port=20601, magic=MAGIC,
         file_path=None):
    """The entry point."""
    remotes = []
    for line in peers:
        addr = Address.parse(line)
        remotes.append(Address(addr))

    # these are the block and tx queues
    # new blocks and txs are pushed to it from the peers
    blockq = queue.Queue()
    txq = queue.Queue()

    # create initial blockchain
    is_first_run = not os.path.exists(BLOCKCHAIN_PATH)

    if file_path == "":
        if is_first_run:
            dirname = os.path.dirname(BLOCKCHAIN_PATH)
            if dirname != "":
                os.makedirs(dirname, exist_ok=True)
            with open(GENESIS_PATH) as f:
                blockchain_json = f.read()
            bc = BlockChain.from_json(blockchain_json)
        else:
            logging.debug(f"Loading blockchain from file: {BLOCKCHAIN_PATH}")
            bc = BlockChain.load_from_file(BLOCKCHAIN_PATH)
    else:
        logging.debug(f"Loading blockchain from file: {file_path}")
        bc = BlockChain.load_from_file(file_path)

    # set blockchain magic
    bc.magic = magic

    # the peer2peer network
    bc.magic = magic
    p2p = P2p(port, remotes, magic, blockq, txq, bc, api_app, api_port, explorer_enabled, explorer_app, explorer_port,
              BLOCKCHAIN_PATH)

    # start the network node
    logging.debug("Starting p2p ...")
    p2p.start()
    p2p.stop()


if __name__ == "__main__":
    ret = False
    args = docopt(USAGE, version=VERSION)
    set_logging(args["-v"])
    logging.debug("cli args: {}".format(args))

    if args["start"]:
        main(int(args["--port"]), args["--peer"], api_port=int(args["--api-port"]),
             explorer_enabled=args["--explorer"], explorer_port=int(args["--explorer-port"]),
             magic=int(args["--magic"]), file_path=args["--file"])
