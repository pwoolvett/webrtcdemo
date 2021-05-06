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
    --net=host \
    nvcr.io/nvidia/deepstream:5.0.1-20.09-samples \
    gst-launch-1.0 $(cat tmp_pipe.gstp | tr "\n" " ")