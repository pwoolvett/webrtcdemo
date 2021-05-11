#!/usr/bin/env python

import os

from app import app
import ray

if __name__ == "__main__":
    ray.init()
    app.run(
        debug=False,
        host=os.environ["FLASK_RUN_HOST"],
        port=os.environ["FLASK_RUN_PORT"],
    )
