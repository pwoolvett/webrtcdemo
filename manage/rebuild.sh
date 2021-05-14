#!/usr/bin/env bash

set -e

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

set -ux

export DISPLAY=:0

xhost + 

docker-compose kill
docker-compose down
docker-compose build \
    && clear \
    && docker-compose up
