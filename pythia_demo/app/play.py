import sys
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst
from gi.repository import GLib

from pythiags.headless import Standalone
from pythiags.headless import GObject
from pythiags.headless import logger
from pythiags.cli import _build_meta_map
from pythiags.cli import pipe_from_file

from app.utils.utils import get_by_name_or_raise
from app.webrtc_client import WebRTCClient

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



mem = None # _build_meta_map(
#     "analytics",
#     "app.extractor:AnalyticsExtractor",
#     "app.consumer:DDBBWriter",
# )
pipeline_str = pipe_from_file("app/pipeline.gstp")

application = Ventanas(pipeline_str, mem)

gstreamer_webrtc_client = WebRTCClient(
    id_=105,
    peer_id=1,
    server="ws://0.0.0.0:8443", # websocket uri  TODO: with net=host in docker-compose this wont work
    pipeline=application.pipeline,
    connection_endpoint="connection"
)

application()
    # TODO ALSO RUN FLASK AND SHIT