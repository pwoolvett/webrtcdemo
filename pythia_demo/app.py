#!/usr/bin/env python
from time import sleep
from flask import Flask

flaskapp = Flask("RMCLabs")

from app.play import gstreamer_webrtc_client

# @flaskapp.route("/start")
# def home():
#     print("HELLO WORLD")
#     return "hello world"

@flaskapp.route("/start", methods = ["GET"])
def start_streaming():
    print("Received request")
    # webrtc_client.open_streaming_connection()
    # return {"STATUS": "Received starting streaming request"} 
    errs=[]
    for _ in range(10):
        try:
            gstreamer_webrtc_client.open_streaming_connection()
            return {"STATUS": "RUNNING"} 
        except Exception as e:
            errs.append({
                "ERROR_TYPE": str(type(e)),
                "ERROR":str(e) 
            })
            sleep(1)
    return {"ERROR_TYPE":"MULTIPLE ERRORS", "ERROR":errs}

if __name__ == "__main__":
    flaskapp.run(
        debug=False,
        host="0.0.0.0",
        port=8000,
        threaded=False
    )
