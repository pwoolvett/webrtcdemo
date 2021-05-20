#!/usr/bin/env bash

#region bash setup
  set -e

  # keep track of the last executed command
  trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
  # echo an error message before exiting
  trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

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

#region clean & re-run compose appliaction
  docker-compose kill
  docker-compose down --remove-orphans
  docker-compose build \
    && clear \
    && docker-compose up \
      --abort-on-container-exit

#endregion

#region convert dot to png

  ./manage/dots

#endregion
