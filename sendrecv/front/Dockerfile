FROM python:3

RUN pip3 install --user flask pyopenssl

WORKDIR /opt/
COPY . /opt/

ENTRYPOINT ["python", "-u", "./app.py"]
CMD []
