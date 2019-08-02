#!/usr/bin/env bash

# FumbleChain CTF (FumbleStore) startup script

function disclaimer() {
  echo "============================================="
  echo "=                DISCLAIMER                 ="
  echo "============================================="
  echo "When running this software on your own machine, you may expose yourself to attacks."
  echo "We cannot guarantee that the software is bug-free."
  echo "Upon starting the FumbleStore, various background services are started."
  echo "These services will listen for incoming connections on multiple TCP ports."
  echo "Proceed with caution and make sure your firewall rules are properly set."
}

function startup() {
  echo "*********************************************"
  echo "*          Starting up FumbleStore          *"
  echo "*********************************************"
  echo "This process usually takes about 3 minutes."
  echo "Please wait..."
}

function post_up() {
  echo "*********************************************"
  echo "*         Accessing the FumbleStore         *"
  echo "*********************************************"
  echo
  echo "The FumbleStore should now be up and running at http://localhost:20801"
  echo
  echo "To shutdown all FumbleChain services, type:"
  echo "docker-compose down"
  echo
}

####################################################
# Main entry point
####################################################

disclaimer
echo
startup
echo

# first generate the necessary common files (wallets/secret keys)
docker build -f docker/init-gen/Dockerfile -t fcgen:latest .
docker run -v $(pwd -P)/gen:/opt/fumblechain/gen fcgen:latest ./gen.sh

# then start the services
docker-compose up --build -d

echo
disclaimer
echo
post_up
echo
