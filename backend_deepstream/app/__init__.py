
import json
from os import environ

from app import consumer
from app import extractor

CERTS_PATH=environ["CERTS_PATH"]
FLASK_RUN_PORT=environ["FLASK_RUN_PORT"]
FLASK_RUN_HOST=environ["FLASK_RUN_HOST"]
LOGLEVEL=environ.get("LOGLEVEL","INFO").upper()
SIGNALING_SERVER = environ["SIGNALLING_SERVER"]

VIDEO_STORAGE=environ["VIDEO_REMOTE_PATH"]
CAMERAS=json.loads(open(environ["CAMERAS_REMOTE_PATH"]).read())

MULTISTREAMTILER_HEIGHT=environ["MULTISTREAMTILER_HEIGHT"]
MULTISTREAMTILER_WIDTH=environ["MULTISTREAMTILER_WIDTH"]
