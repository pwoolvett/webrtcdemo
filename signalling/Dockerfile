FROM python:3

RUN pip3 install --user websockets

WORKDIR /opt/signalling
COPY . /opt/signalling

ENTRYPOINT [ "python","-u","./simple_server.py"]
# ENTRYPOINT [ "python","-u","./simple_server.py","--disable-ssl" ]
CMD ["--cert-path", "/opt/signalling"]
