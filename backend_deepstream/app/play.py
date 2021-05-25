import os
from pathlib import Path
import sys

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst

from pythiags.headless import Standalone
from pythiags.headless import GObject
from pythiags.cli import _build_meta_map

from app import CAMERAS
from app import MULTISTREAMTILER_HEIGHT
from app import MULTISTREAMTILER_WIDTH
from app import SIGNALING_SERVER
from app import VIDEO_STORAGE

from app.webrtc_client import WebRTCClient
from app.recorder import MultiVideoRecorder
from app.utils.utils import get_by_name_or_raise
from app.utils.utils import pipe_from_file
from app.utils.utils import datetime
from app.utils.utils import _to_dot

from logger import logger

class Ventanas(Standalone):
    def run(self):
        # TODO: ver como matar
        self.loop = GObject.MainLoop()
        self.pipeline.set_state(Gst.State.PLAYING)
        # TODO WE SHOUD RUN THIS SOMEWHERE SO WE CAN KILL THE APPLICATION IF GSTREAM<ER GOES DOWN
        # TOGHETHER WITH THE bus_call & friends
        # try:
        #     self.loop.run()
        # except Exception as exc:
        #     logger.warning("Exc")
        #     logger.error(exc)
        #     raise
        # finally:
        #     self.stop()

    @property
    def muxer(self):
        return get_by_name_or_raise(self.pipeline, "muxer")

    @property
    def tiler(self):
        return get_by_name_or_raise(self.pipeline, "tiler")

    @property
    def cameras(self):
        available_cameras = {}
        muxer_pads = {
            int(camera_id.name.lstrip("sink_"))
            for camera_id in self.muxer.pads
            if "sink" in str(camera_id.direction).lower()
        }

        for camera_id, camera in CAMERAS.items():
            if int(camera_id) not in muxer_pads:
                logger.warning(f"Camera {camera_id} could not be retrieved. Please check its connection")
                continue
            available_cameras[camera_id] = camera
        logger.info(f"Available cameras: {available_cameras}")
        return available_cameras
        

    def focus_camera(self, camera_id):  # TODO: handle wrong number
        result = self.tiler.set_property("show-source", camera_id)
        return {"status": "OK", "result": str(result)}

    def dump_dot(self):
        name=str(datetime.datetime.now()).replace(":", "_")
        _to_dot(name, self.pipeline)
        return name

    def on_eos(self, bus, message):
        print("Gstreamer: End-of-stream")
        self.join()

    def on_error(self, bus, message):
        err, debug = message.parse_error()
        print("Gstreamer: %s: %s" % (err, debug))

mem = _build_meta_map(
    "analytics",
    "app.extractor:AnalyticsExtractor",
    "app.consumer:DDBBWriter",
)


pipeline_str = pipe_from_file(
    "app/pipeline.gstp.jinja",
    cameras=CAMERAS,
    multistreamtiler_width=MULTISTREAMTILER_HEIGHT,
    multistreamtiler_height=MULTISTREAMTILER_WIDTH,
    
)
logger.debug(pipeline_str)

application = Ventanas(
    pipeline_str,
    mem
)

gstreamer_webrtc_client = WebRTCClient(
    id_=105,
    server=SIGNALING_SERVER,
    pipeline=application.pipeline,
    connection_endpoint="connection",
)


application(
    control_logs=False
)


# # TODO: this must be performed after application runs because we need application.cameras
# maybe we could use a gsttreamer probe instead
for j in range(5):
    cams = application.cameras
    logger.info(f"cams={cams}")
    if cams:
        break
    from time import sleep;sleep(1)
else:
    raise RuntimeError("no cameras found")


video_recorder = MultiVideoRecorder(
    application.cameras,
    pipeline=application.pipeline,
    fps=30,
    window_size=2,
    sink_location_prefix=str(Path(VIDEO_STORAGE)/"event_")
)

extractor, consumer = mem["analytics"]
consumer.set_video_recorder(video_recorder)  # TODO: monkey banana solve this
