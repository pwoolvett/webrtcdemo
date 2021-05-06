FROM python:3.6.9

RUN apt-get update && \
    apt-get install -y \
        python3-opencv

COPY ./frontend_flask/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./frontend_flask /opt
COPY models.py /opt/app/models.py

WORKDIR /opt

ENV SECRET_KEY="RMCLabsDVEN2021"
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "app.py"]
CMD []
