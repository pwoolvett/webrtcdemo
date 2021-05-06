FROM nvcr.io/nvidia/deepstream:5.0.1-20.09-samples

RUN apt-get update \
  && apt-get install -y \
    python3-pip \
    pkg-config \
    libcairo2-dev \
    libsdl2-ttf-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libgirepository1.0-dev \
    libgstreamer1.0 \
    libgstreamer-plugins-base1.0-dev \
    gir1.2-gst-plugins-bad-1.0 \
    && python3 -m pip install --upgrade pip

RUN apt-get update \
  && apt-get install -y \
    libjson-glib-dev \
    python-gst-1.0 \
    gir1.2-gst-plugins-bad-1.0 \
    gstreamer1.0-nice \
    libcairo2-dev \
    gstreamer1.0-plugins-*




ADD ./backend_deepstream/requirements.txt requirements.txt
RUN python3 -m pip install --user -r requirements.txt

COPY ./backend_deepstream /opt
ADD models.py /opt/models.py

WORKDIR /opt

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "app.py"]
