#!/usr/bin/env bash

# create parent dir if not exists
mkdir -p $(dirname ${FUMBLECHAIN_BLOCKCHAIN_PATH})

# create initial blockchain contents
if [ ! -f ${FUMBLECHAIN_BLOCKCHAIN_PATH} ]; then
  python3 -m utils.ch2_genesis_maker | tee ${FUMBLECHAIN_BLOCKCHAIN_PATH}
fi

# run the node
./daemon.py -vvv --port ${CH2_MAINNET_NODE_PORT} --magic ${CH2_MAINNET_MAGIC} start
