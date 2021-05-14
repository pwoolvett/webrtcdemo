#!/usr/bin/env python

import os

from app import app


if __name__ == "__main__":
    app.run(
        debug=False,
        host=os.environ["FLASK_RUN_HOST"],
        port=os.environ["FLASK_RUN_PORT"],
    )
