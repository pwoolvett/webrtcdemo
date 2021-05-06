#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""""""
import datetime
import collections
import datetime
import enum
import sys
from time import sleep

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst
from gi.repository import GLib

from app.utils.logger import logger
from app.utils.utils import dotted
from app.utils.utils import traced
from app.utils.utils import run_later

Gst.init(None)

FRAMES_PER_SECOND=30
RUNTIME_MINUTES=20

# DO NOT THESE
SEC_PER_MINUTE = 60
RUNTIME_SECONDS=RUNTIME_MINUTES*SEC_PER_MINUTE
NUM_BUF = RUNTIME_SECONDS*FRAMES_PER_SECOND

DEFAULT_WINDOW_SIZE_SEC=2

CAPS = ",".join([
    "video/x-raw",
    "format=YV12",
    "width=1280",
    "height=720",
    f"framerate={FRAMES_PER_SECOND}/1",
    # "multiview-mode=mono",
    # "pixel-aspect-ratio=1/1",
    # "interlace-mode=progressive",
])


PIPE_RAW = f"""
videotestsrc
  num-buffers={NUM_BUF}
  is-live=true
  name=videotestsrc
! video/x-raw,width=320,height=240
! timeoverlay
  halignment=right
  valignment=bottom
  text="Stream time:"
  shaded-background=true
  font-desc="Sans, 24"
! tee
  name=t1

t1.
! queue
! xvimagesink

t1.
! queue
! appsink
  name=appsink
  emit-signals=true
  async=false
"""

class VideoRecorder:
    """

        def demo_boilerplate():

            def build_pipeline():
                pipeline_string = "\n".join(
                    line.split("#",1)[0]
                    for line in PIPE_RAW.split("\n")
                    if not line.strip().startswith("#")
                ).strip()
                return Gst.parse_launch(pipeline_string)

            def on_message(bus, message, loop, pipeline):
                t = message.type
                if t == Gst.MessageType.EOS:
                    logger.info("End-of-stream\n")
                    loop.quit()
                elif t == Gst.MessageType.ERROR:
                    err, debug = message.parse_error()
                    logger.error("Error: %s: %s\n" % (err, debug))
                    loop.quit()

                return True

            loop = GLib.MainLoop()

            pipeline = build_pipeline()
            pipeline_bus = pipeline.get_bus()
            pipeline_bus.add_signal_watch()
            pipeline_bus.connect("message", on_message, loop, pipeline)

            pipeline.set_state(Gst.State.PLAYING)

            return pipeline, loop

        def main():
            window_size = 2
            pipeline, loop = demo_boilerplate()

            rec = VideoRecorder(pipeline, FRAMES_PER_SECOND, window_size)


            for delay in range(3, RUNTIME_SECONDS-window_size, 5):
                run_later(rec.record, delay)

            try:
                loop.run()
            finally:
                loop.quit()
                pipeline.set_state(Gst.State.NULL)
    """
    RECORD_BIN_STRING = f"""
        appsrc
          name=appsrc
          emit-signals=true
          is-live=true
          do-timestamp=true
          stream-type=0
          format=time
        ! {CAPS}
        ! queue
          flush-on-eos=false
        ! x264enc
        ! avimux
        ! filesink
          location="{{sink_location}}.avi"
          name=filesink
    """

    class States(enum.Enum):
        IDLE = None
        STARTING = "starting"
        RECORDING = "recording"
        FINISHING = "finishing"


    def __init__(
        self,
        pipeline,
        fps,
        window_size=DEFAULT_WINDOW_SIZE_SEC,
        sink_location_prefix="vids/out_",
        wait_start_msec=3000,
        running_since=None,
        appsink_name="appsink",
    ):
        """

        Important:

        * Pipeline must have raw image bufers and contain an `appsink` named "appsink".
        * `self.appsrc.emit('push-buffer', gstbuf)` should push buffers
          ASAP, not in `on_new_sample` callback
        
        """
        self.pipeline = pipeline
        self.fps = fps
        self.window_size = window_size
        self.wait_start_msec = wait_start_msec
        self.running_since = running_since or datetime.datetime.now()
        self.sink_location_prefix = f"{sink_location_prefix}_{self.running_since}_"

        self.record_bin = None
        self._record_count = -1
        self._pending_cancel = None

        self.state = self.States.IDLE

        self.deque = collections.deque(maxlen=fps*window_size)
        self.appsink_name = appsink_name
        self.appsink = self.get_appsink()
        self.appsink.connect(
            'new-sample',
            self.on_new_sample
        )
        self.appsrc = None

    def on_new_sample(self, *a) -> Gst.FlowReturn:

        sample = self.appsink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        buffer: Gst.Buffer = sample.get_buffer()
        buffer_size = buffer.get_size()
        data=buffer.extract_dup(0, buffer_size)
        self.deque.append(data)

        if self.state == self.States.RECORDING:
            try:
                state = self.appsrc.get_state(Gst.CLOCK_TIME_NONE)
                if Gst.State.PLAYING not in state:  # TODO: Warning: comparing different enum types: GstState and GstStateChangeReturn
                    logger.debug(f"NOPE - State: {state}")
                    return Gst.FlowReturn.OK
                data = self.deque.popleft()
                gstbuf = Gst.Buffer.new_wrapped(data)
                self.appsrc.emit('push-buffer', gstbuf)
            except AttributeError as exc:
                logger.error(f"NO APPSRC: {exc}")
            except IndexError:
                logger.error("empty queue")

        return Gst.FlowReturn.OK

    def reset_stop_recording_timeout(self):
        if self._pending_cancel:
            self._pending_cancel.cancel()
            self._pending_cancel = None
        self._pending_cancel = run_later(
            self._stop_recording,
            2*self.window_size,  # once backwards (as incoming buffers are delayd by window_size), once into the future.
        )

    @traced(logger.debug)
    def record(self):

        # avoid race condition when two threads call same code
        if self._pending_cancel:
            self._pending_cancel.cancel()
            self._pending_cancel = None

        if self.state == self.States.IDLE:
            self.state = self.States.STARTING

            self._record_count +=1
            name = f"{self.running_since}_{self._record_count}"
            run_later(self._start_recording, 0, name=name)
            self.reset_stop_recording_timeout()
            self.wait_for_bin(True)
            return self.current_video_location

        if self.state == self.States.RECORDING:
            self.reset_stop_recording_timeout()
            return self.current_video_location

        if self.state == self.States.STARTING:
            logger.info(f"Recording already starting - rescheduling...")
            r = run_later(self.record, 1)
            r.join()
            return r._output


        if self.state == self.States.FINISHING:
            logger.info(f"Recording finising previous state - re-scheduling record event")
            r = run_later(self.record, 1e-3)
            r.join()
            return r._output

        raise NotImplementedError(f"Unhandled state: {self.state}")


    @property
    def current_video_location(self):
        filesink = self.record_bin.get_by_name("filesink")
        location = filesink.get_property("location")
        return location

    @traced(logger.info)
    def wait_for_bin(self, exist, niter=10):

        prefix = "No record bin" if exist else "Record bin still present"
        msg = f"{prefix} after {(int(self.wait_start_msec/1e3))}[s]"
        for _ in range(niter):
            if (
                exist and bool(self.record_bin)
            ) or (
                (not exist) and (not self.record_bin)
            ):
                break
            sleep(self.wait_start_msec/(niter*1e3))
        else:
            raise TimeoutError(msg)
        return



    @dotted
    @traced(logger.info)
    def _start_recording(self, name):
        app_sink = self.appsink.get_static_pad('sink')

        add = app_sink.add_probe(
            Gst.PadProbeType.BUFFER,
            self._connect_bin,
            name
        )
        if not add:
            logger.error("Could not add probe")
            sys.exit(42)


    @dotted
    @traced(logger.debug)
    def _connect_bin(self, pad, info, name):
        self._create_record_bin(name)

        add = self.pipeline.add(self.record_bin)
        if not add:
            logger.error("Could not add record_bin to pipeline")
            sys.exit(42)

        synced = self.record_bin.sync_state_with_parent()
        if not synced:
            logger.error("Could not sync record_bin with pipeline")
            sys.exit(42)

        if not self.record_bin.sync_children_states():
            logger.error("Could not sync record_bin with children")
            sys.exit(42)
        self.appsrc = self.record_bin.get_by_name('appsrc')
        self.state = self.States.RECORDING
        return Gst.PadProbeReturn.REMOVE

    @traced(logger.debug)
    def _release_bin(self):
        self.record_bin.set_state(Gst.State.NULL)
        self.record_bin.unref()  # TODO: check why we get gobject warnings... are they important?
        self.state = self.States.IDLE
        self.record_bin = None

    def _check_eos(
        self,
        pad: Gst.Pad,
        info: Gst.PadProbeInfo,
    ):
        event_type = info.get_event().type
        if event_type == Gst.EventType.EOS:
            name = self.current_video_location.rstrip(".avi")
            removed = self.pipeline.remove(self.record_bin)
            # Can't set the state of the src to NULL from its streaming thread
            GLib.idle_add(self._release_bin)
            # record_bin.unref() TODO: use this if there are memleaks 
            if not removed:
                logger.error("BIN remove FAILED")
                sys.exit(42)
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    @traced(logger.debug)
    def _create_record_bin(self, name):
        self.record_bin = Gst.parse_bin_from_description(
            self.RECORD_BIN_STRING.format(
                sink_location=f"{self.sink_location_prefix}{name}"
            ),
            True
        )

        filesink = self.record_bin.get_by_name("filesink")
        filesink_pad = filesink.get_static_pad("sink")

        filesink_pad.add_probe(
            Gst.PadProbeType.EVENT_BOTH,
            self._check_eos,
        )

    @traced(logger.debug)
    def _disconnect_bin(self, pad, info):
        record_bin = self.record_bin

        if not record_bin:
            logger.debug("Record bin already unset! Removing blocking pad on tee...")
            return Gst.PadProbeReturn.REMOVE

        record_bin.send_event(Gst.Event.new_eos())
        return Gst.PadProbeReturn.REMOVE

    def get_appsink(self):
        appsink= self.pipeline.get_by_name(self.appsink_name)
        if not appsink:
            raise NameError(f"Unable to find {self.appsink_name}")
        return appsink

    @traced(logger.info)
    def _stop_recording(self):
        if not self.record_bin:
            logger.debug(f"Record bin already removed - skipping stop recording")
            return
        self.state = self.States.FINISHING
        appsink = self.get_appsink()  # TODO: cant we justself.appsink here?
        appsink_src = appsink.get_static_pad('sink')
        appsink_src.add_probe(
            Gst.PadProbeType.BLOCK,
            self._disconnect_bin,
        )


class MultiVideoRecorder:

    def __init__(
        self,
        cameras,
        appsink_fmt="appsink_",
        **recorder_kw

    ):
        recorder_kw.setdefault("running_since", datetime.datetime.now())
        self.recorders = {
            camera: VideoRecorder(
                appsink_name=f"{appsink_fmt}{camera}",
                **recorder_kw
            )
            for camera in cameras
        }

    def record(self, source_id):
        recorder = self.recorders[source_id]
        return recorder.record()

# s = pad.get_current_caps().get_structure(0)
# width, height, fps = (
#     s.get_value(cap)
#     for cap in 
#     ('width', "height", "framerate")
# )

