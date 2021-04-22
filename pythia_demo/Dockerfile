FROM nvcr.io/nvidia/deepstream:5.0.1-20.09-samples

RUN apt-get update \
    && apt-get install -y python3-pip \
                        pkg-config \
                        libcairo2-dev \
                        libsdl2-ttf-dev \
                        libsdl2-dev \
                        libsdl2-image-dev \
                        libsdl2-mixer-dev \
                        libgirepository1.0-dev \
                        libgstreamer1.0 \
                        libgstreamer-plugins-base1.0-dev

# COPY requirements.txt requirements.txt
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --ignore-installed pythiags[cli]==0.9.0 && \
    python3 -m pip install SQLAlchemy

RUN python3 -m pip uninstall --yes Kivy-Jetson && \
    python3 -m pip install Kivy

COPY ./pythia_demo /opt
ADD models.py /opt/models.py

RUN cd /opt/pyds_ext && \
    python3 -m pip install .

WORKDIR /opt
ENV PYTHONPATH='/opt'
ENV DISPLAY=:1

ENTRYPOINT ["pygst-launch","--file=pipeline.gstp","--obs=analytics","--ext=demo:MyCustomExtract","--proc=demo:MyCustomProcess"]
CMD []