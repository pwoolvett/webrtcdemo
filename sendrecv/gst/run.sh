#!/usr/bin/env bash

xhost + 

export DISPLAY=:0

rm -rf /home/rmclabs/RMCLabs/webrtcdemo/sendrecv/gst/*.jp*g

docker run \
    --rm \
    -v /home/rmclabs/RMCLabs/webrtcdemo/sendrecv/gst:/opt \
    --env DISPLAY=$DISPLAY \
    --env PYTHONUNBUFFERED=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    gstreamer_test \
    python3 gst.py
    