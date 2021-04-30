#!/usr/bin/env python

from app import app
from app import webrtc_client

@app.route("/start", methods = ["GET"])
def start_streaming():
    webrtc_client.open_streaming_connection()
    return {"STATUS": "Received starting streaming request"} 
    # try:
    #     webrtc_client.open_streaming_connection()
    #     return {"STATUS": "RUNNING"} 
    # except Exception as e:
    #     return {
    #         "ERROR_TYPE": str(type(e)),
    #         "ERROR" 
    #         }


if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=8000,
        threaded=False
    )
