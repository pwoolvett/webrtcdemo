#!/usr/bin/env bash

xhost + 

export DISPLAY=:0


sudo rm -rf memory.log

watch -b -d -c -t -n1 'echo $(date --iso=sec): "$(free --mega | grep Mem | tr -s " " "\n" | head -n 3 | tail -n 1) [mb]" >> memory.log' &>/dev/null &
watchpid=$!

rm -rf /home/rmclabs/RMCLabs/webrtcdemo/sendrecv/gst/*.jp*g

docker run \
    --rm \
    -v /home/rmclabs/RMCLabs/webrtcdemo/sendrecv/gst:/opt \
    --env DISPLAY=$DISPLAY \
    --env PYTHONUNBUFFERED=1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    gstreamer_test \
    python3 gst.py

kill $watchpid
