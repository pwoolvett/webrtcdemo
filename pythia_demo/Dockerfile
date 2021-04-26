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
    && python3 -m pip install --upgrade pip

RUN python3 -m pip install --user \
    pythiags[gpu,ds,cli]==0.10.0 \
    SQLAlchemy==1.4.7

COPY ./pythia_demo /opt
ADD models.py /opt/models.py

ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH='/opt'
ENV DISPLAY=:0

WORKDIR /opt

ENTRYPOINT ["pygst-launch","--file=pipeline.gstp","--obs=analytics","--ext=demo:MyCustomExtract","--proc=demo:MyCustomProcess"]
CMD []
