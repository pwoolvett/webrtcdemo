FROM python:3.6.9

COPY ./sendrecv/front/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./sendrecv/front /opt
COPY models.py /opt/models.py

WORKDIR /opt

ENTRYPOINT ["python", "./app.py"]
CMD []
