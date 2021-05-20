#!/usr/bin/env python3

import contextlib
from functools import partial
from multiprocessing import Process
from pathlib import Path
from typing import Union

from flask import Flask
from pythiags.headless import Standalone
from pythiags.headless import GObject
from pythiags.headless import Gst

def pipe_from_file(
    path: Union[str, Path],
    **pipeline_kwargs
) -> str:
    print(f"Loading pipeline from {path}")

    real = Path(path).resolve()
    with open(real) as fp:
        pipeline_string = fp.read()
    lines = []
    for line in pipeline_string.split("\n"):
        raw = line.strip()
        content = raw.split("#", 1)[0]
        if content.strip():
            lines.append(content)
    pipeline_string = "\n".join(lines)
    try:
        formatted_pipeline = pipeline_string.format_map(pipeline_kwargs)
    except KeyError as exc:
        print(f"PythiaGsApp: Cannot run {real}. Reason: {repr(exc)}")
        raise

    return formatted_pipeline










video_endpoint = Flask("RMCLabs")


@video_endpoint.route(
    "/test/<string>", methods=["GET"]
)  # TODO use post instead
def focus_camera(string: str):
    return {
        "STATUS": "OK",
        "value": string,
    }

@video_endpoint.route("/stop", methods=["GET"])
def focus_camdera():
    # video_endpoint.gstreamer.stop()
    response = video_endpoint.gstreamer.pipeline.set_state(Gst.State.NULL)
    print(f"stop pipe response:{response}")
    return {
        "STATUS": "OK",
        "value": "stopped",
        "gst": str(video_endpoint.gstreamer),
        "loop": str(video_endpoint.gstreamer.loop),
    }



class Ventanas(Standalone):

    def __init__(self, flask_app, *a, **kw):
        super().__init__(*a, **kw)
        self.flask_app = flask_app
        self.flask_app.gstreamer = self
        self.flask_server = None

    def run(self):
        print("setting loop")
        self.loop = GObject.MainLoop()
        print("loop set")
        self.pipeline.set_state(Gst.State.PLAYING)
        print(f"before try loop:{self.loop}")
        with self.inject_flask(self.flask_app):
            try:
                self.loop.run()
            except Exception as exc:
                print(f"Exception loop:{self.loop}")
                print("Exc")
                print(exc)
                raise
            finally:
                print("TEERMINATINGINGING APP RUN")
                print(f"finally try loop:{self.loop}")
                if self.loop:
                    self.stop()

    @contextlib.contextmanager
    def inject_flask(self, flask_app, *a, **kw):
        print("CALLING inject_flask")
        if self.flask_server:
            raise ValueError("A flask_server has already been defined")
        print("DI NOT RAISE flask_server")
        target = partial(flask_app.run, *a, **kw)
        self.flask_server = Process(target=target)
        
        try:
            print("before prc start")
            self.flask_server.start()
            print("prc starteed")
            yield
        except Exception as exc:
            print(exc)
            raise
        finally:
            print("TEERMINATINGINGING FLAK CTXMAN")
            self.flask_server.terminate()
            self.flask_server.join()
            self.flask_server = None
            # self.stop()

    def stop(self):
        print("PythiaGsHeadless: Stopping")
        self.pipeline.set_state(Gst.State.NULL)
        print("PythiaGsHeadless: calling self.join")
        self.join()
        self.loop.quit()

    
    

pipeline_str = pipe_from_file("app/pipeline_mp.gstp")


application = Ventanas(
    video_endpoint,
    pipeline_str,
    None,  # mem
)

if __name__ == "__main__":
    application()
