#!/usr/bin/env bash

# FumbleChain CTF (FumbleStore) startup script

# first generate the necessary common files (wallets/secret keys)
docker build -f docker/init-gen/Dockerfile -t fcgen:latest .
docker run -v $(pwd -P)/gen:/opt/fumblechain/gen fcgen:latest ./gen.sh

# then start the services
docker-compose up --build
