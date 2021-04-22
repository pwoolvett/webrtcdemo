from models import get_session
from models import get_engine
from models import create_database
import sqlalchemy

db_connection_string = "sqlite:////db/test.db"
Session = get_session(db_connection_string)
create_database(get_engine(db_connection_string))