
import flask


# Create the application.
APP = flask.Flask(__name__)


@APP.route('/')
def index():
    """Display the index page accessible at '/'."""
    return flask.render_template('index.html')

@APP.route('/live')
def live():
    """Display the live stream, accesible at '/live'."""
    return flask.render_template('live.html')

@APP.route('/live2')
def live2():
    """Display the live stream, accesible at '/live'."""
    return flask.render_template('live2.html')

@APP.route('/registry')
def registry():
    """Display the registry page accessible at '/registry'."""
    return flask.render_template('registry.html')

@APP.route('/stats')
def stats():
    """Display the index page accessible at '/stats'."""
    return flask.render_template('stats.html')

if __name__ == '__main__':
    from pathlib import Path
    parent = Path(__file__).parent
    APP.run(
        debug=True,
        host="0.0.0.0",
        port="80",
        ssl_context=(str(parent / 'cert.pem'), str(parent / 'key.pem'))
    )
