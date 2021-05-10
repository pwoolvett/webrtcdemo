import flask
from flask import render_template
from flask import request

import requests

from app import app
from app.forms import TimeFilterForm
from app.models import get_session
from app.stats import EventStatistics
from app.registry import RegistryStatistics


DBSession = get_session(app.config["SQLALCHEMY_DATABASE_URI"])
# DBSession = get_session("sqlite:////home/rmclabs/RMCLabs/webrtcdemo/db/test.db")


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/live")
def play_stream():
    return flask.render_template("live.html")


@app.route("/registry", methods=["GET", "POST"])
def registry():
    """Display the registry page accessible at '/registry'."""
    form = TimeFilterForm()
    if request.method == "GET":
        return render_template("registry.html", form=form)
    else:
        if form.validate_on_submit():
            events = RegistryStatistics.build_from_form(form, DBSession)
            print(f"Found {len(events.render())} events")
            return render_template("registry.html", events=events.render(), form=form)
        else:
            raise ValueError  # TODO: 404


@app.route("/stats", methods=["GET", "POST"])
def stats():
    """Display the index page accessible at '/stats'."""
    form = TimeFilterForm()
    if request.method == "GET":
        return render_template("stats.html", form=form)
    else:
        if form.validate_on_submit():
            stats = EventStatistics.build_from_form(form, DBSession)
            return render_template("stats.html", results=stats.render(), form=form)
        else:
            raise ValueError  # TODO: 404
