FROM maxmcd/gstreamer:1.14-buster

RUN apt-get --allow-releaseinfo-change update \
    && apt-get install -y \
        libjson-glib-dev \
        python3-pip \
        python-gst-1.0 \
        gir1.2-gst-plugins-bad-1.0 \
        gstreamer1.0-nice \
        libcairo2-dev \
        gstreamer1.0-plugins-*

RUN python3 -m pip install  \
    asn1crypto==0.24.0 \
    cryptography==2.6.1 \
    entrypoints==0.3 \
    gobject==0.1.0 \
    keyring==17.1.1 \
    keyrings.alt==3.1.1 \
    pycairo==1.20.0 \
    pycrypto==2.6.1 \
    PyGObject==3.30.4 \
    pyxdg==0.25 \
    SecretStorage==2.3.1 \
    six==1.12.0 \
    websockets==8.1


WORKDIR /opt/
COPY . /opt/

# RUN make

# CMD echo "Waiting a few seconds for you to open the browser at localhost:8080" \
#     && sleep 10 \
#     && ./webrtc-sendrecv \
#     --peer-id=1 \
#     --server=ws://signalling:8443 \
#     --disable-ssl
ENV PYTHONUNBUFFERED=1

ENTRYPOINT [ "python3", \
  "webrtc_sendrecv.py", \
  "--server=wss://signalling:8443", \
  "1" \
]
CMD []
