from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from app.config import Config

app = Flask(__name__)

app.config.from_object(Config)
db = SQLAlchemy(app)

# app.config['AREAS_PER_CAM'] = get_cams()#TODO Implementar
app.config["AREAS_PER_CAM"] = {0: "Camara ejemplo"}
