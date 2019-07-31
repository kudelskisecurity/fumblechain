#!/usr/bin/env python3

"""FumbleChain CLI client"""

import argparse
import cmd
import datetime
import multiprocessing
import sys
import time
import traceback

from api.api_wrapper import API
from model import transaction, wallet
from model.block import Block

USER_WALLET = wallet.Wallet()
DO_HELP_WALLET = "_do_help_wallet"


def show_transaction(trans):
    fmt = f"""--------------------------------------------
Transaction:{trans.index}
Hash:       {trans.get_hash()}
Source:     {trans.src}
Destination:{trans.dst}
Amount:     {trans.qty}
Signature:  {trans.signature}
--------------------------------------------"""
    print(fmt)


def show_block(block):
    fmt = f"""
============================================
Block       #{block.index}
Hash:       {block.get_hash()}
Previous:   {block.prevhash}
Target:     {block.target}
Merkle tree:{block.trans_tree.root.get_hash()}
Timestamp:  {time.asctime(time.gmtime(block.timestamp))}

Transactions:"""
    print(fmt)
    for t in block.get_transactions():
        show_transaction(t)
    print("============================================")


def mine(tx, api):
    """Mine a block"""
    i = 0
    while True:
        b = api.new_block(tx)
        start_time = datetime.datetime.utcnow().timestamp()
        while (datetime.datetime.utcnow().timestamp() - start_time < 30):
            if b.validate_proof(proof=str(i)):
                b.proof = str(i)
                sys.stdout.flush()
                return b, api
            i += 1


def miner_push_block(res):
    """Push mined block using the API.
    This is a callback function called by the multiprocessing.Pool instance."""
    b, api = res
    api.push_block(b)
    print()
    print("[info] Successfully mined block")
    print(FumblechainCli.prompt, end="")
    sys.stdout.flush()


def mine_error(e):
    """Print mining errors.
    This is a callback function called by the multiprocessing.Pool instance."""
    print(e)
    print(traceback.format_exc())
    print(sys.exc_info())


MINING_POOL = multiprocessing.Pool(processes=1)


class FumblechainCli(cmd.Cmd):
    intro = """================================
FumbleChain v1.0
Type help or ? to list commands.
================================"""
    prompt = "fumblechain > "

    def show_subcommand_help(self, subcommand):
        print("Invalid subcommand")
        self.do_help(subcommand)

    def do_quit(self, arg):
        """Quits the FumbleChain CLI"""
        self.close()
        return True

    # Handle ctrl+d
    do_EOF = do_quit

    def do_wallet(self, arg):
        """Wallet management
generate        Generate a new wallet
show            Show current wallet
save <filename> Saves the wallet to a file
load <filename> Load a wallet from a file"""
        global USER_WALLET
        args = arg.split()

        if len(arg) == 0:
            self.typecmd("help wallet")
            return

        if args[0] == "generate":
            USER_WALLET.create_keys()
        elif args[0] == "show":
            try:
                print("Wallet info")
                print(f"Address: {USER_WALLET.get_address()}")
                print(f"Balance: {self.api.get_balance(USER_WALLET.get_address())}")
            except:
                print("No wallet configured")
                self.typecmd("help wallet")
        elif args[0] == "save":
            if len(args) == 2:
                USER_WALLET.save_key(args[1])
            else:
                print("Missing file name")
        elif args[0] == "load":
            if len(args) == 2:
                USER_WALLET = wallet.Wallet.load_keys(args[1])
            else:
                print("Missing file name")
        else:
            self.typecmd("help wallet")
            return

    def complete_wallet(self, text, line, begidx, endidx):
        cmds = ["generate", "show", "save", "load"]
        return [i for i in cmds if i.startswith(text)]

    def do_transaction(self, arg):
        """Send coins to address. Usage: transaction <destination> <amount>"""
        global USER_WALLET
        try:
            source_address = USER_WALLET.get_address()
        except:
            print("Wallet not configured")
            self.typecmd("help wallet")
            return
        args = arg.split()
        if len(args) == 2:
            address = args[0]
            amount = args[1]
        else:
            address = input("enter recipient address : ")
            amount = input("enter amount : ")
        try:
            amount = float(amount)
        except ValueError:
            print("Incorrect amount")
            return
        magic = api.get_magic()
        t = transaction.Transaction(source_address, address, amount, magic=magic)
        USER_WALLET.sign_transaction(t)

        if self.api.push_transaction(t):
            print("OK")
        else:
            print("KO")

    def do_transaction_raw(self, arg):
        """Send raw transaction from JSON"""
        tx_json = input("enter transaction JSON : ")
        try:
            tx = transaction.Transaction.from_json(tx_json)
        except ValueError:
            print("Invalid transaction JSON")
            return

        if self.api.push_transaction(tx):
            print("OK")
        else:
            print("KO")

    def do_block_raw(self, arg):
        """Send raw block from JSON"""
        block_json = input("enter block JSON : ")
        try:
            blk = Block.from_json(block_json)
        except ValueError:
            print("Invalid block JSON")
            return

        if self.api.push_block(blk):
            print("OK")
        else:
            print("KO")

    def do_show(self, arg):
        """Show a blockchain object. Usage: show <type> <arg>
Available types :
transaction <transaction_id>    Show a specific transaction
block <block_id>                Show a block contents
transaction_json                Show transaction JSON
block_json                      Show block JSON
"""
        args = arg.split()
        if len(args) != 2:
            print("Not enough arguments")
            self.typecmd("help show")
            return

        if args[0] == "transaction":
            tx = self.api.get_tx(args[1])
            if tx is not None:
                show_transaction(tx)
            else:
                print("Cannot find transaction")
        elif args[0] == "transaction_json":
            tx = self.api.get_tx(args[1])
            if tx is not None:
                print(tx.to_json())
            else:
                print("Cannot find transaction")
        elif args[0] == "block":
            blk = self.api.get_block(args[1])
            if blk is not None:
                show_block(blk)
            else:
                print("Cannot find block")
        elif args[0] == "block_json":
            blk = self.api.get_block(args[1])
            if blk is not None:
                print(blk.to_json())
            else:
                print("Cannot find block")
        else:
            print("Invalid subcommand")
            self.typecmd("help show")
            return

    def complete_show(self, text, line, begidx, endidx):
        cmds = ["transaction", "block", "transaction_json", "block_json"]
        return [i for i in cmds if i.startswith(text)]

    def do_debug(self, arg):
        """Debugging commands. Usage: debug <arg>
Available args :
transaction_pool    Show the actual transactions in the pool
mining              Show the current mined block
peers               Show the connected peers
magic               Show the magic number for this blockchain
"""
        if arg == "transaction_pool":
            print("Transaction pool :")
            for tx in self.api.get_transaction_pool():
                show_transaction(tx)
        elif arg == "mining":
            pass
        elif arg == "peers":
            print("Peers list:")
            for peer in self.api.get_peers():
                print(peer)
        elif arg == "magic":
            magic = api.get_magic()
            print(magic)
        else:
            print("Invalid subcommand")
            self.typecmd("help debug")
            return

    def complete_debug(self, text, line, begidx, endidx):
        cmds = ["transaction_pool", "mining", "peers", "magic"]
        return [i for i in cmds if i.startswith(text)]

    def do_mine(self, arg):
        """Miner control. Usage: mine <start|stop>"""
        if arg == "start":
            global USER_WALLET
            try:
                source_address = USER_WALLET.get_address()
            except:
                print("Wallet not configured")
                self.typecmd("help wallet")
                return
            global MINING_POOL
            magic = api.get_magic()
            t = transaction.Transaction("0", USER_WALLET.get_address(), 1, magic=magic)
            print("Starting miner")
            sys.stdout.flush()
            MINING_POOL.apply_async(mine, (t, self.api), callback=miner_push_block, error_callback=mine_error)
        elif arg == "stop":
            pass
        else:
            print("Invalid subcommand")
            self.typecmd("help mine")
            return

    def complete_mine(self, text, line, begidx, endidx):
        cmds = ["start", "stop"]
        return [i for i in cmds if i.startswith(text)]

    def close(self):
        pass

    def emptyline(self):
        pass

    def default(self, line):
        super().default(line)
        self.typecmd("help")

    def typecmd(self, command, interval=0.085):
        print(FumblechainCli.prompt, end="")
        self.stdout.flush()
        for c in command:
            time.sleep(interval)
            print(c, end="")
            self.stdout.flush()
        time.sleep(0.2)
        print()
        self.stdout.flush()
        self.onecmd(command)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FumbleChain CLI client")
    default_api_url = "http://localhost:1337/"
    parser.add_argument("-H", "--api-url", dest="api_url",
                        help=f"URL to connect to. Default is {default_api_url}.",
                        default=default_api_url)
    args = parser.parse_args()

    API_URL = args.api_url
    print(f"Using API: {API_URL}")

    api = API(args.api_url)
    cli = FumblechainCli()
    cli.api = api
    cli.cmdloop()
