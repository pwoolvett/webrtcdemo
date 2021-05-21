#!/usr/bin/env bash

#region bash setup
  set -e

  # keep track of the last executed command
  # trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
  # echo an error message before exiting
  # trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

  set -ux

#endregion

#region experiment cleanup

  sudo rm -rf ./debug/dots/
  mkdir -p ./debug/dots/

  sudo rm -rf ./debug/videos/
  mkdir -p ./debug/videos/

#endregion

#region X server setup
  export DISPLAY=:0
  xhost + 
#endregion

#region experiment data path definition
  now=`date +"%Y_%m_%d__%H_%M_%S"`
#endregion

#region pipeline definition from file
  pipeline=$($(dirname $(realpath $0))/gstp-parse $(dirname $(realpath $0))/wip.gstp)
#endregion


# #region docker run
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
# #endregion


./manage/dots
