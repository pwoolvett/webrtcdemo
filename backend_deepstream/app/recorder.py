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

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst
from gi.repository import GLib

from app.utils.utils import dotted
from app.utils.utils import traced
from app.utils.utils import run_later

from logger import logger

Gst.init(None)

GLib.threads_init()

FRAMES_PER_SECOND = 30
RUNTIME_MINUTES = 20

# DO NOT THESE
SEC_PER_MINUTE = 60
RUNTIME_SECONDS = RUNTIME_MINUTES * SEC_PER_MINUTE
NUM_BUF = RUNTIME_SECONDS * FRAMES_PER_SECOND

DEFAULT_WINDOW_SIZE_SEC = 2

# CAPS = ",".join(
#     [
#         "video/x-raw",
#         "format=YV12",
#         "width=1280",
#         "height=720",
#         f"framerate={FRAMES_PER_SECOND}/1",
#     ]
# )


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
                logger.debug("End-of-stream\n")
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
          caps={{caps}}
        ! vp8enc
          deadline=1
        ! webmmux
        ! filesink
          location={{sink_location}}.webm
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
        sink_location_prefix="/videos/event",
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
        self.sink_location_prefix = sink_location_prefix

        self.record_bin = None
        self._record_count = -1
        self._pending_cancel = None

        self.state = self.States.IDLE

        self.deque = collections.deque(maxlen=fps * window_size)
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
        data = buffer.extract_dup(0, buffer_size)
        self.deque.append(data)

        if self.state == self.States.RECORDING:
            try:
                logger.info("ZZZZ: RECEIVED BUFFER IN RECORDING STATE")
                state_change_return, current, pending = self.pipeline.get_state(1000)  # TODO: handle possible outcomes better
                state = self.appsrc.get_state(Gst.CLOCK_TIME_NONE)
                # if (current != Gst.State.PLAYING) or (pending != Gst.State.VOID_PENDING):
                #     logger.info(f"ZZZZ: Not pushing buffer - PIPELINEState: {(state_change_return, current, pending)}")
                #     logger.info(f"ZZZZ: Not pushing buffer - APPSRCState: {state}")
                #     return Gst.FlowReturn.OK
                logger.info(f"ZZZZ: Pushing buffer - State: {state}")
                data = self.deque.popleft()
                gstbuf = Gst.Buffer.new_wrapped(data)
                self.appsrc.emit("push-buffer", gstbuf)
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
            2
            * self.window_size,  # once backwards (as incoming buffers are delayd by window_size), once into the future.
        )

    # @dotted
    @traced(logger.info)
    def record(self):
        logger.debug(f"self.state: {self.state}")
        state_change_return, current, pending = self.pipeline.get_state(1000)
        logger.debug(f"self.pipeline.get_state(1000): {(state_change_return, current, pending)}")
        # avoid race condition when two threads call same code
        if self._pending_cancel:
            self._pending_cancel.cancel()
            self._pending_cancel = None

        if self.state == self.States.IDLE:
            self.state = self.States.STARTING

            self._record_count += 1
            run_later(self._start_recording, 0, name=str(self._record_count))
            self.reset_stop_recording_timeout()
            self.wait_for_bin(True)
            return self.current_video_location

        if self.state == self.States.RECORDING:
            logger.info(f"Recording already recording...")
            self.reset_stop_recording_timeout()
            return self.current_video_location

        if self.state == self.States.STARTING:
            logger.info(f"Recording already starting - rescheduling...")
            r = run_later(self.record, 1)
            r.join()
            return r._output

        if self.state == self.States.FINISHING:
            logger.info(
                f"Recording finising previous state - re-scheduling record event"
            )
            r = run_later(self.record, 1e-3)
            r.join()
            return r._output

        raise NotImplementedError(f"Unhandled state: {self.state}")

    @property
    def current_video_location(self):
        filesink = self.record_bin.get_by_name("filesink")
        location = filesink.get_property("location")
        return location

    @traced(logger.debug)
    def wait_for_bin(self, exist, niter=10):

        prefix = "No record bin" if exist else "Record bin still present"
        msg = f"{prefix} after {(int(self.wait_start_msec/1e3))}[s]"
        for _ in range(niter):
            if (exist and bool(self.record_bin)) or (
                (not exist) and (not self.record_bin)
            ):
                break
            sleep(self.wait_start_msec / (niter * 1e3))
        else:
            raise TimeoutError(msg)
        return self.record_bin

    # @dotted
    @traced(logger.debug)
    def _start_recording(self, name):
        app_sink = self.appsink.get_static_pad('sink')
        caps_raw = app_sink.get_current_caps()
        # s = caps_raw.get_structure(0)
        # capstuple = [
        #     s.get_value(cap)
        #     for cap in
        #     ('width', "height", "framerate", "format")
        # ]
        add = app_sink.add_probe(
            Gst.PadProbeType.BUFFER,
            self._connect_bin,
            name,
            caps_raw
        )
        if not add:
            logger.error("Could not add probe")
            sys.exit(42)
        return "_start_recording: SUCCESS"

    @traced(logger.info)
    @dotted
    def _connect_bin(self, pad, info, name, caps):
        caps_str = caps.to_string().replace(", ", ",")
        logger.info(f"caps_str: `{caps_str}`")  # TODO: use logger.debug
        logger.info(f"PIPELINE STATE: (state_change_return, current, pending)={self.pipeline.get_state(Gst.CLOCK_TIME_NONE)}")
        try:
            self._create_record_bin(name, caps_str)
        except GLib.Error as exc:
            logger.error(f"Could not add record_bin to pipeline - reason: {type(exc)}({exc})")
            sys.exit(42)
            print(f"TODO EXIT HERE\n"*10)
            return Gst.PadProbeReturn.REMOVE
        
        add = self.pipeline.add(self.record_bin)
        if not add:
            logger.error("Could not add record_bin to pipeline")
            sys.exit(42)

        try:
            synced = self.record_bin.sync_state_with_parent()
            if not synced:
                logger.error("Could not sync record_bin with pipeline")
                sys.exit(42)
            logger.error(f"SYNC RESULT: {synced}")
            logger.info(f"PIPELINE STATE CON TIMEOUT POST PARENT: (state_change_return, current, pending)={self.pipeline.get_state(1000)}")
            logger.info("Successfully syncd record_bin state to pipeline's")


            if not self.record_bin.sync_children_states():
                logger.error("Could not sync record_bin with children")
                sys.exit(42)
            logger.info("Successfully synced record_bin's state to its childrens'")
            logger.info(f"PIPELINE STATE CON TIMEOUT POST CHILDREN: (state_change_return, current, pending)={self.pipeline.get_state(1000)}")



            self.appsrc = self.record_bin.get_by_name("appsrc")
            
            self.state = self.States.RECORDING
            logger.info(f"PIPELINE STATE after change{self.state}")
            
            logger.info(f"Attempting state change to play")
            play_state = self.pipeline.set_state(Gst.State.PLAYING)
            logger.info(f"Play state result: {play_state}")

            return Gst.PadProbeReturn.REMOVE
        except BaseException as exc:
            logger.error("se cayo la wea")
            logger.exception(exc)
            raise
        finally:
            return Gst.PadProbeReturn.REMOVE

    @traced(logger.warning)
    def _release_bin(self):
        self.record_bin.set_state(Gst.State.NULL)
        self.record_bin.unref()  # TODO: check why we get gobject warnings... are they important?
        self.state = self.States.IDLE
        self.record_bin = None

    @traced(logger.error)
    def _check_eos(
        self,
        pad: Gst.Pad,
        info: Gst.PadProbeInfo,
    ):
        event_type = info.get_event().type
        if event_type == Gst.EventType.EOS:
            logger.info("CHECK_EOS: received EOS - removing bin")
            name = self.current_video_location.rstrip(".avi")
            removed = self.pipeline.remove(self.record_bin)
            # Can't set the state of the src to NULL from its streaming thread
            #GLib.idle_add(self._release_bin)  # TODO ESTA WEAS ES PELIGROSA - REVISAR MEMLEAK
            run_later(self._release_bin, 0)
            # record_bin.unref() TODO: use this if there are memleaks
            if not removed:
                logger.error("BIN remove FAILED")
                sys.exit(42)
            return Gst.PadProbeReturn.DROP
        return Gst.PadProbeReturn.OK

    @dotted
    @traced(logger.warning)
    def _create_record_bin(self, name, caps_raw):
        caps = caps_raw
        # caps=",".join([
        #     'video/x-raw',
        #     'width=704',
        #     'height=480',
        #     'format=I420'
        # #     # 'multiview-mode=(string)mono',
        # #     # 'multiview-flags=(GstVideoMultiviewFlagsSet)0:ffffffff:/right-view-first/left-flipped/left-flopped/right-flipped/right-flopped/half-aspect/mixed-mono',
        # #     # 'framerate=(fraction)30/1',
        # #     # 'batch-size=(int)2',
        # #     # 'num-surfaces-per-frame=(int)1',
        # ])
        bin_str = self.RECORD_BIN_STRING.format(
            sink_location=f"{self.sink_location_prefix}{name}",
            element_name=name,
            caps=caps,
            
        )

        logger.info(f"BIN STRING: ```{bin_str}```")
        self.record_bin = Gst.parse_bin_from_description(
            bin_str,
            True,
        )

        filesink = self.record_bin.get_by_name("filesink")
        filesink_pad = filesink.get_static_pad("sink")

        filesink_pad.add_probe(
            Gst.PadProbeType.EVENT_BOTH,
            self._check_eos,
        )
        return self.record_bin

    @dotted
    @traced(logger.info)
    def _disconnect_bin(self, pad, info):
        record_bin = self.record_bin

        if not record_bin:
            logger.info("Record bin already unset! Removing blocking pad on tee...")
            return Gst.PadProbeReturn.REMOVE

        logger.info("ASCHEDULING RECORD BIN REMOVAL, then removing blocking pad on tee...")
        record_bin.send_event(Gst.Event.new_eos())
        return Gst.PadProbeReturn.REMOVE

    def get_appsink(self):
        appsink= self.pipeline.get_by_name(self.appsink_name)
        if not appsink:
            raise NameError(f"Unable to find {self.appsink_name}")
        return appsink

    @traced(logger.debug)
    def _stop_recording(self):
        if not self.record_bin:
            logger.debug(f"Record bin already removed - skipping stop recording")
            return
        self.state = self.States.FINISHING
        appsink = self.get_appsink()  # TODO: cant we just use self.appsink here?
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
        
        sink_location_prefix = recorder_kw.pop("sink_location_prefix")
        self.recorders = {}
        for camera in cameras:
            self.recorders[camera] = VideoRecorder(
                appsink_name=f"{appsink_fmt}{camera}",
                sink_location_prefix=f"{sink_location_prefix}{camera}_",
                **recorder_kw
            )

    def record(self, source_id):
        print(f"Available recorders: {self.recorders}")
        recorder = self.recorders[source_id]
        return recorder.record()
