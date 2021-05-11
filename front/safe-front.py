#!/usr/bin/env python

from app import app
import ray

if __name__ == "__main__":
    ray.init()
    app.run(
        debug=False,
        host="0.0.0.0",
        port=8888,
    )
