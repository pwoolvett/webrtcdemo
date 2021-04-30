#!/usr/bin/env python
from time import sleep
from app import app
from app import webrtc_client

@app.route("/start", methods = ["GET"])
def start_streaming():
    print("Received request")
    # webrtc_client.open_streaming_connection()
    # return {"STATUS": "Received starting streaming request"} 
    errs=[]
    for _ in range(10):
        try:
            webrtc_client.open_streaming_connection()
            return {"STATUS": "RUNNING"} 
        except Exception as e:
            errs.append({
                "ERROR_TYPE": str(type(e)),
                "ERROR":str(e) 
            })
            sleep(1)
    return {"ERROR_TYPE":"MULTIPLE ERRORS", "ERROR":errs}

if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=8000,
        threaded=False
    )
