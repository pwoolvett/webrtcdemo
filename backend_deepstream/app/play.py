import sys
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst

from pythiags.headless import Standalone
from pythiags.headless import GObject
from pythiags.cli import _build_meta_map
from pythiags.cli import pipe_from_file

from app.webrtc_client import WebRTCClient
from app.recorder import VideoRecorder
from app.utils.utils import get_by_name_or_raise
from app.utils.utils import pipe_from_file

class Ventanas(Standalone):

    def run(self):
        #TODO: ver como matar
        self.loop = GObject.MainLoop()
        self.pipeline.set_state(Gst.State.PLAYING)
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
        return [
            str(pad)
            for pad in self.muxer.pads
            if "sink" in str(pad.direction).lower()
        ]

    def focus_camera(self, camera_id):  # TODO: handle wrong number
        result = self.tiler.set_property("show-source", camera_id)
        return {"status": "OK", "result": str(result)}

mem = _build_meta_map(
    "analytics",
    "app.extractor:AnalyticsExtractor",
    "app.consumer:DDBBWriter",
)

pipeline_str = pipe_from_file("app/pipeline.gstp")
print("\n"*10)
print(pipeline_str)
print("\n"*10)

application = Ventanas(pipeline_str, mem)

gstreamer_webrtc_client = WebRTCClient(
    id_=105,
    # peer_id=1,
    # server="ws://0.0.0.0:9999/signalling", # websocket uri  TODO: with net=host in docker-compose this wont work
    server="ws://localhost:7003", # websocket uri
    pipeline=application.pipeline,
    connection_endpoint="connection"
)

# video_recorder = VideoRecorder(
#     application.pipeline, 
#     fps=30, 
#     window_size=2
# )
video_recorder = None

# extractor, consumer = mem["analytics"]
# consumer.set_video_recorder(video_recorder)

application()
# application.loop.run()  # TODO: remove these to re-enable flask
# import sys;sys.exit()   # TODO: remove these to re-enable flask