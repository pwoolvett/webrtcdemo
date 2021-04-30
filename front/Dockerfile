FROM python:3.6.9

RUN apt-get update && \
    apt-get install -y \
        python3-opencv

COPY ./front/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./front /opt
COPY models.py /opt/app/models.py

WORKDIR /opt

ENV SECRET_KEY="RMCLabsDVEN2021"

ENTRYPOINT ["python", "safe-front.py"]
CMD []
