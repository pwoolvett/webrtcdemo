#!/usr/bin/env python

import os
from pathlib import Path

from app import app

if __name__ == "__main__":
    certs_path = Path(os.environ["CERTS_PATH"])

    app.run(
        debug=False,
        host=os.environ["FLASK_RUN_HOST"],
        port=os.environ["FLASK_RUN_PORT"],
        ssl_context=(str(certs_path / "cert.pem"), str(certs_path / "key.pem")),
    )
