#!/usr/bin/env python3

import asyncio
import json
import ssl
import sys

import gi

gi.require_version("Gst", "1.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst
from gi.repository import GLib
from gi.repository import GstWebRTC
from gi.repository import GstSdp
import websockets
from websockets.uri import parse_uri


from utils import get_by_name_or_raise
from utils import traced_async
from utils import traced
from utils import start_asyncio_background

FPS=30
RUNTIME_SEC=600

TEST_BIN = """
    queue
    ! jpegenc 
    ! multifilesink location={}_frame%d.jpeg
"""
    
SRC_PIPELINE = f"""
  videotestsrc
    is-live=true
    pattern=ball
    num-buffers={str(int(FPS*RUNTIME_SEC))}
  ! timeoverlay
    font-desc="Sans, 36"
    halignment=center
    valignment=center
  ! tee
    name=connection
  
  connection.
  ! queue
  ! xvimagesink
  """

class GstPlayer:
    STREAMING_BIN = """
        queue
        ! videoconvert
        ! queue
        ! vp8enc
          deadline=1
        ! rtpvp8pay
        ! queue 
        ! application/x-rtp,media=video,encoding-name=VP8,payload=97
        ! webrtcbin
          name=sendrecv
          bundle-policy=max-bundle
          stun-server=stun://stun.l.google.com:19302
        """

    def __init__(
        self,
        webrtcclient,
        pipeline: Gst.Pipeline,
        connection_endpoint:str = "connection"
    ):
        self.pipeline = pipeline
        self.webrtcclient = webrtcclient
        self.connection_endpoint:Gst.Element.Tee = get_by_name_or_raise(pipeline, connection_endpoint)
        self.streaming_bin = None
        self.webrtc_bin = None

    def start_streaming(self, ) -> None:
        self.streaming_bin = Gst.parse_bin_from_description(self.STREAMING_BIN, True)
        self._connect_webrtc_signals() # FIXME: also disconnect signals when hanging
        self.connect_streaming_bin()   # TODO: link and sync states in a buffer probe

    def _connect_webrtc_signals(self, ):
        self.webrtc_bin = self.streaming_bin.get_by_name("sendrecv")
        self.webrtc_bin.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.webrtc_bin.connect("on-ice-candidate", self.webrtcclient.send_ice_candidate_message)
        # self.webrtc_bin.connect("pad-added", self.on_incoming_stream)

    def on_negotiation_needed(self, element: Gst.Element) -> None:
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        element.emit("create-offer", None, promise)

    def on_offer_created(self, promise, _, __) -> None:
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value("offer")
        promise = Gst.Promise.new()
        self.webrtc_bin.emit("set-local-description", offer, promise)
        promise.interrupt()
        self.webrtcclient.send_sdp_offer(offer)

    def stop_streaming(self, ) -> None:
        # self.disconnect_streaming_bin() # TODO: link and sync states in a buffer probe
        self.streaming_bin = None  # TODO maybe also unlink to avoid memleak
        self.webrtc_bin = None  # TODO maybe also unlink to avoid memleak

    def connect_streaming_bin(self) -> None:
        connection_pad = self.connection_endpoint.get_static_pad('sink')
        connection_pad.add_probe(Gst.PadProbeType.BUFFER, self.connect_bin_callback)

    def connect_bin_callback(self, pad: Gst.Pad, info):
        if not self.pipeline.add(self.streaming_bin):
            sys.exit(42)
        if not pad.parent.link(self.streaming_bin):
            sys.exit(45)
        self.streaming_bin.sync_state_with_parent()
        return Gst.PadProbeReturn.REMOVE

    def disconnect_webrtcbin(self, ):
        sinkpad = self.connection_endpoint.get_static_pad('src_1')  # TODO: Get static pad de forma mas robusta
        sinkpad.add_probe(
            Gst.PadProbeType.BUFFER,
            self.disconnect_bin_callback
        )
        return GLib.SOURCE_REMOVE

    def disconnect_bin_callback(self, pad: Gst.Pad, info):
        peer = pad.get_peer()  
        pad.unlink(peer)
        self.streaming_bin.set_state(Gst.State.NULL)
        self.pipeline.remove(self.streaming_bin)
        #video_bin.unref() TODO avoid memoryleak
        return Gst.PadProbeReturn.REMOVE



class WebRTCClient:
    @traced
    def __init__(
        self,
        id_: int,
        peer_id: int,
        server: str, # websocket uri
        pipeline: Gst.Pipeline, 
        connection_endpoint: str
    ):
        self.id_ = id_
        self.conn = None
        # self.webrtc = None
        self.peer_id = peer_id
        if not server:
            raise ValueError
        self.server = server or "wss://webrtc.nirbheek.in:8443"

        self.player = GstPlayer(self, pipeline, connection_endpoint)


        # self.server = 'wss://webrtc.nirbheek.in:8443'

    @traced_async
    async def connect(self):
        wsuri = traced(parse_uri)(self.server)
        if wsuri.secure:
            sslctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        else:
            sslctx = None
        self.conn = await websockets.connect(self.server, ssl=sslctx)
        await self.conn.send("HELLO %d" % self.id_)

    async def setup_call(self):
        await self.conn.send("SESSION {}".format(self.peer_id))

    def send_sdp_offer(self, offer):
        text = offer.sdp.as_text()
        print("Sending offer:\n%s" % text)
        msg = json.dumps({"sdp": {"type": "offer", "sdp": text}})
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.conn.send(msg))
        loop.close()


    def send_ice_candidate_message(self, _, mlineindex, candidate):
        icemsg = json.dumps(
            {"ice": {"candidate": candidate, "sdpMLineIndex": mlineindex}}
        )
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.conn.send(icemsg))
        loop.close()


    def open_streaming_connection(self, ):
        client_loop = asyncio.get_event_loop()
        client_loop.run_until_complete(self.connect())
        start_asyncio_background(self.connection_monitor, client_loop)

    @property
    def webrtc(self):
        return self.player.webrtc_bin

    @property
    def pipe(self):
        return self.player.pipe

    def handle_sdp(self, message):
        assert self.webrtc
        msg = json.loads(message)
        if "sdp" in msg:
            sdp = msg["sdp"]
            assert sdp["type"] == "answer"
            sdp = sdp["sdp"]
            print("Received answer:\n%s" % sdp)
            res, sdpmsg = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
            answer = GstWebRTC.WebRTCSessionDescription.new(
                GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg
            )
            promise = Gst.Promise.new()
            self.webrtc.emit("set-remote-description", answer, promise)
            promise.interrupt()
        elif "ice" in msg:
            ice = msg["ice"]
            candidate = ice["candidate"]
            sdpmlineindex = ice["sdpMLineIndex"]
            self.webrtc.emit("add-ice-candidate", sdpmlineindex, candidate)

    def close_streaming_connection(self):
        self.player.stop_streaming()

    async def connection_monitor(self):
        assert self.conn
        async for message in self.conn:
            if message == "HELLO":
                await self.setup_call()
            elif message == "SESSION_OK":
                self.player.start_streaming()
            elif message.startswith("ERROR"):
                print(message)
                self.close_streaming_connection()
                return 1
            else:
                self.handle_sdp(message)
        self.close_streaming_connection()
        return 0

    async def stop(self):
        if self.conn:
            await self.conn.close()
        self.conn = None



def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write(f"Error: {err}: {debug}\n")
        loop.quit()
    return True


if __name__=="__main__":
    Gst.init(None)
    pipe = Gst.parse_launch(SRC_PIPELINE)
    
    gstreamer_loop = GLib.MainLoop()

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, gstreamer_loop)
    
    webrtc_client =  WebRTCClient(
        id_=105,
        peer_id=1,
        server="ws://signalling:8443", # websocket uri
        pipeline=pipe, 
        connection_endpoint="connection"
    )

    pipe.set_state(Gst.State.PLAYING)
    # ESTOS SIMULAN UNA INCOMING CALL / HANG
    
    GLib.timeout_add(10000, webrtc_client.open_streaming_connection)

    try:
        gstreamer_loop.run()
    except:
        pass
    
