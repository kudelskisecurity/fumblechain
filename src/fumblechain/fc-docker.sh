#!/usr/bin/env bash

# wrapper script for running the FumbleChain node via docker
# this script considerably shortens the length of commands that players would have to type otherwise

function print_usage() {
  echo "Usage: fc-docker.sh [OPTION]..."
  echo
  echo "  -p, --port"
  echo "                 daemon port"
  echo "  -n, --name"
  echo "                 docker container name"
  echo "  -i, --image"
  echo "                 docker image name"
  echo "  -P, --api-port"
  echo "                 daemon API port"
  echo "  -E, --explorer-port"
  echo "                 daemon blockchain explorer port"
  echo "  -H, --host"
  echo "                 daemon peer host:port"
  echo "  -h, --help"
  echo "                 show this message and exit"
}

# parse CLI arguments
extra_args=()

while [ "$1" != "" ]; do
  case "$1" in
  -p | --port)
    port="$2"
    shift
    ;;
  -n | --name)
    name="$2"
    shift
    ;;
  -i | --image)
    image="$2"
    shift
    ;;
  -P | --api-port)
    api_port="$2"
    shift
    ;;
  -E | --explorer-port)
    explorer_port="$2"
    shift
    ;;
  -H | --host)
    host="$2"
    shift
    ;;
  -h | --help)
    print_usage
    exit
    ;;
  *)
    extra_args+=("$1")
    ;;
  esac
  shift
done

docker build -t fc .
docker run -it --rm -p ${port}:${port} -p ${explorer_port}:${explorer_port} --network fumblechain_default --name ${name} ${image} /bin/sh -c \
  "./daemon.sh -vvv --explorer --explorer-port ${explorer_port} --port ${port} --api-port ${api_port} --peer ${host} ${extra_args[@]} start"
