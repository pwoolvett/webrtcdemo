#!/usr/bin/env bash

export DISPLAY=:0
xhost + 

docker run \
    --runtime=nvidia \
    --rm \
    -it \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    --env DISPLAY=:0 \
    --env GST_DEBUG_DUMP_DOT_DIR=/dump \
    -v $PWD/gst_logs:/dump \
    -v `pwd`/debug/dots/`date --iso=sec | tr ":-" "_"`:/opt/dots \
    -v `pwd`/debug/wip.gstp:/opt/wip.gstp \
    -v `pwd`/debug/launch:/opt/launch \
    --net=host \
    -w /opt \
    --entrypoint ./launch \
    nvcr.io/nvidia/deepstream:5.0.1-20.09-samples
