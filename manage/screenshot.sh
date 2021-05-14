#!/usr/bin/env bash
export DISPLAY=:0
export fname=debug/`date +"%Y_%m_%d__%H_%M_%S"`.png
gnome-screenshot -f $fname
echo 'Remote Screenshot saved to "'$fname'"'
