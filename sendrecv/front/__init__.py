from pathlib import Path

app = Flask(__name__)

db_location = Path(__file__).parent / "test.db"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = f"sqlite:///{db_location}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
db.create_all()
