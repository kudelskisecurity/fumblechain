# FumbleChain p2p node

# Usage

For example, start 3 nodes that connect to each other:

```bash
# terminal 1
$ ./daemon.py start -vvv

# terminal 2
$ ./daemon.py start --port 2223 --peer=2222 -vvv

# terminal 3
$ ./daemon.py start --port 2224 --peer=2222 --peer=2223 -vvv
```

# Testing

To run unit tests, simply execute:

```bash
./test.py
```

# Note on utils

Do not run scripts with a main() in the utils package directly.

Run them as modules, for example:

```
python3 -m utils.genkey | tee my.wallet | python3 -m utils.pubkey  | tee my.pubkey

```
