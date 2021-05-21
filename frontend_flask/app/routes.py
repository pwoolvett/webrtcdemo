import flask
from flask import render_template
from flask import request

from app import app
from app.forms import TimeFilterForm
from app.models import get_session
from app.stats import EventStatistics
from app.registry import RegistryStatistics


DBSession = get_session(app.config["SQLALCHEMY_DATABASE_URI"])

@app.route("/")
def index():
    return flask.render_template("index.jinja")


@app.route("/live")
def play_stream():
    return flask.render_template("live.jinja")


@app.route("/registry", methods=["GET", "POST"])
def registry():
    """Display the registry page accessible at '/registry'."""
    form = TimeFilterForm()
    if request.method == "GET":
        return render_template("registry.jinja", form=form)
    else:
        if form.validate_on_submit():
            events = RegistryStatistics.build_from_form(form, db_session_constructor=DBSession)
            rendered=events()
            print(f"Found {len(rendered)} events")
            return render_template("registry.jinja", events=rendered, form=form)
        else:
            raise ValueError  # TODO: 404


@app.route("/stats", methods=["GET", "POST"])
def stats():
    """Display the index page accessible at '/stats'."""
    form = TimeFilterForm()
    if request.method == "GET":
        return render_template("stats.jinja", form=form)
    else:
        if form.validate_on_submit():
            stats = EventStatistics.build_from_form(form, db_session_constructor=DBSession)
            rendered=stats()
            # rendered = 
            return render_template("stats.jinja", results=rendered, form=form)
        else:
            raise ValueError  # TODO: 404
