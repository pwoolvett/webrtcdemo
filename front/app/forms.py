from datetime import date
from datetime import time

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField
from wtforms.fields.html5 import TimeField
from wtforms import SubmitField

from app import app

AVAILABLE_CAMERAS = app.config["AVAILABLE_CAMERAS"]


class TimeFilterForm(FlaskForm):
    date_from = DateField(
        "Start Date", default=date(2021, 1, 1), validators=[DataRequired()]
    )
    date_to = DateField(
        "End Date", default=date(2021, 12, 31), validators=[DataRequired()]
    )
    time_from = TimeField(
        "Start Time", default=time(0, 0, 0), validators=[DataRequired()]
    )
    time_to = TimeField(
        "End Time", default=time(23, 59, 59), validators=[DataRequired()]
    )
    camera_id = SelectField(
        "Camera ID",
        choices=[(key, value) for key, value in enumerate(AVAILABLE_CAMERAS)],
        validators=[DataRequired()],
    )
    submit = SubmitField("View results")