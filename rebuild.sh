#!/usr/bin/env bash
export DISPLAY=:0

xhost + 

docker-compose down
docker-compose build
docker-compose up 
