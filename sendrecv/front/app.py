import flask
from flask import Flask

app = Flask(__name__)

db_location = "/db/test.db"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"sqlite:///{db_location}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/live')
def play_stream():
    return flask.render_template('live.html')


@app.route('/registry')
def registry():
    """Display the registry page accessible at '/registry'."""
    return flask.render_template('registry.html')


@app.route('/stats')
def stats():
    """Display the index page accessible at '/stats'."""
    return flask.render_template('stats.html')


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=80,
    )