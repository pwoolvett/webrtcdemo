#!/usr/bin/env python3

import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst
from gi.repository import GLib

FPS=30
RUNTIME_SEC=15
CONNECT_DELAY_SEC=4
DISCONNECT_DELAY_SEC=7

WEBRTC_BIN = """
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
    name=t

  t.
  ! queue
  ! xvimagesink
  """

FULL_PIPELINE = """
  videotestsrc
    is-live=true
    pattern=ball
  ! timeoverlay
    font-desc="Sans, 36"
    halignment=center
    valignment=center
  ! tee
    name=t
  t.
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

TEST_PIPELINE = """
    videotestsrc
    is-live=true
    pattern=ball
  ! timeoverlay
    font-desc="Sans, 36"
    halignment=center
    valignment=center
  ! autovideosink
"""	

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

def connect_webrtcbin(pipe):
    print("Connecting")
    tee = pipe.get_by_name("t")
    sinkpad = tee.get_static_pad('sink')
    sinkpad.add_probe(Gst.PadProbeType.BUFFER, connect_bin_callback, pipe)
    return GLib.SOURCE_REMOVE


def disconnect_webrtcbin(pipe):
    print("Disconnecting")
    tee = pipe.get_by_name("t")
    sinkpad = tee.get_static_pad('src_1')
    sinkpad.add_probe(
        Gst.PadProbeType.BUFFER,
        disconnect_bin_callback,
        pipe
    )
    return GLib.SOURCE_REMOVE


count=-1
def connect_bin_callback(pad, info, pipeline):
    global count 
    count+=1
    bin_str = TEST_BIN.format(count)
    video_bin = Gst.parse_bin_from_description(bin_str, True)
    if not pipeline.add(video_bin):
        sys.exit(42)
    if not pad.parent.link(video_bin):
        sys.exit(45)
    video_bin.sync_state_with_parent()
    return Gst.PadProbeReturn.REMOVE


def disconnect_bin_callback(pad, info, pipeline):
    peer = pad.get_peer()  # video_bin.get_static_pad("sink")
    pad.unlink(peer)
    video_bin = peer.parent
    video_bin.set_state(Gst.State.NULL)
    pipeline.remove(video_bin)
    #video_bin.unref() TODO avoid memoryleak
    return Gst.PadProbeReturn.REMOVE


class GstPlayer:
    @traced
    def __init__(
        self,
        webrtcclient,
    ):
        self.pipe = None
        self.webrtcclient = webrtcclient

    def start_pipeline(self, source_pipeline):
        self.webrtc_bin = Gst.parse_bin_from_description(WEBRTC_BIN_PIPELINE)
        self.pipe = Gst.parse_launch(PIPELINE_DESC)  # TODO cambiar por Gst,parse_bin_from_descriptiuon y conectar a la pipa preexistente
        self.webrtc = self.pipe.get_by_name("sendrecv")
        self.webrtc.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.webrtc.connect("on-ice-candidate", self.webrtcclient.send_ice_candidate_message)
        self.webrtc.connect("pad-added", self.on_incoming_stream)
        self.pipe.set_state(Gst.State.PLAYING)
        

    def on_negotiation_needed(self, element):
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        element.emit("create-offer", None, promise)

    def on_offer_created(self, promise, _, __):
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value("offer")
        promise = Gst.Promise.new()
        self.webrtc.emit("set-local-description", offer, promise)
        promise.interrupt()
        self.webrtcclient.send_sdp_offer(offer)

    def on_incoming_stream(self, _, pad):
        if pad.direction != Gst.PadDirection.SRC:
            return

        decodebin = Gst.ElementFactory.make("decodebin")
        decodebin.connect("pad-added", self.on_incoming_decodebin_stream)
        self.pipe.add(decodebin)
        decodebin.sync_state_with_parent()
        self.webrtc.link(decodebin)

    def on_incoming_decodebin_stream(self, _, pad):
        if not pad.has_current_caps():
            print(pad, "has no caps, ignoring")
            return

        caps = pad.get_current_caps()
        assert len(caps)
        s = caps[0]
        name = s.get_name()
        if name.startswith("video"):
            q = Gst.ElementFactory.make("queue")
            conv = Gst.ElementFactory.make("videoconvert")
            sink = Gst.ElementFactory.make("autovideosink")
            self.pipe.add(q, conv, sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad("sink"))
            q.link(conv)
            conv.link(sink)
        elif name.startswith("audio"):
            q = Gst.ElementFactory.make("queue")
            conv = Gst.ElementFactory.make("audioconvert")
            resample = Gst.ElementFactory.make("audioresample")
            sink = Gst.ElementFactory.make("autoaudiosink")
            self.pipe.add(q, conv, resample, sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad("sink"))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)

    def close_pipeline(self):
        self.pipe.set_state(Gst.State.NULL)
        self.pipe = None
        self.webrtc = None




if __name__=="__main__":
    Gst.init(None)
    pipe = Gst.parse_launch(SRC_PIPELINE)
    
    # pdata = ProbeData(pipe, src)
    loop = GLib.MainLoop()

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # ESTOS SIMULAN UNA INCOMING CALL / HANG
    GLib.timeout_add(4000, connect_webrtcbin, pipe)
    GLib.timeout_add(7000, disconnect_webrtcbin, pipe)

    # ESTOS SIMULAN UNA INCOMING CALL / HANG
    GLib.timeout_add(8000, connect_webrtcbin, pipe)
    GLib.timeout_add(10000, disconnect_webrtcbin, pipe)

    # ESTOS SIMULAN UNA INCOMING CALL / HANG
    GLib.timeout_add(11000, connect_webrtcbin, pipe)
    GLib.timeout_add(12000, disconnect_webrtcbin, pipe)

    # start play back and listen to events
    pipe.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    
    # # cleanup
    # pipe.set_state(Gst.State.NULL)