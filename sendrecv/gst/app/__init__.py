
from flask import Flask

from app.gstreamer_webrtc import Gst
from app.gstreamer_webrtc import GLib
from app.gstreamer_webrtc import GstPlayer
from app.gstreamer_webrtc import WebRTCClient
from app.gstreamer_webrtc import bus_call
from app.gstreamer_webrtc import SRC_PIPELINE

app = Flask("RMCLabs")

Gst.init(None)
pipe = Gst.parse_launch(SRC_PIPELINE)

gstreamer_loop = GLib.MainLoop()

bus = pipe.get_bus()
bus.add_signal_watch()
bus.connect ("message", bus_call, gstreamer_loop)

webrtc_client =  WebRTCClient(
    id_=105,
    peer_id=1,
    server="ws://signalling:8443", # websocket uri  TODO: with net=host in docker-compose this wont work
    pipeline=pipe,
    connection_endpoint="connection"
)

pipe.set_state(Gst.State.PLAYING)

# ESTOS SIMULAN UNA INCOMING CALL / HANG

# GLib.timeout_add(10000, webrtc_client.open_streaming_connection)

# try:

#     gstreamer_loop.run()
# except:
#     pass




