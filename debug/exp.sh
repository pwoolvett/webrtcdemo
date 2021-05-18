#!/usr/bin/env bash

sudo rm -rf debug/videos/*
sudo rm -rf debug/dots/*

export DISPLAY=:0
xhost +

now=`date +"%Y_%m_%d__%H_%M_%S"`

pipeline=$($(dirname $(realpath $0))//gstp-parse $(dirname $(realpath $0))/wip.gstp)


docker run \
    --runtime=nvidia \
    --rm \
    -it \
    --net=host \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /opt \
    -v `pwd`/debug/dots/$now:/opt/dots \
    -v `pwd`/debug/videos/$now:/videos \
    --env DISPLAY=:0 \
    --env GST_DEBUG_DUMP_DOT_DIR=/opt/dots \
    --env GST_DEBUG=2 \
    --entrypoint gst-launch-1.0 \
    rmclabs-io/ventanas-backend_deepstream \
    -e $pipeline
    # --entrypoint bash \
    # nvcr.io/nvidia/deepstream:5.0.1-20.09-samples \
