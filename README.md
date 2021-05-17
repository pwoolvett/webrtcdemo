# pilotoventanas
piloto SAFE powered by oddl para electrowinning codelco ventanas

The code is split into several components:

backend This application takes care of: 1.1 running a gstreamer+deepstream+pythia pipeline 1.2 extracting metadta, storing it in a database 1.3 stream video using webrtcbin pipeline element

frontend

signalling Scaffolding required for WebRTC connections

data processing

Generate metrics from database query
generate histogram from database query
TODO: Maybe expose functionality via an API?
Demo
run docker-compose build
run docker-compose up
Within 10 seconds, open a browser into localhost:8080
wait for 10 seconds to timeout, and video should start playing
TODO
make backend/apt.list smaller