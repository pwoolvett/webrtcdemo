import cv2
import pandas as pd
from contextlib import contextmanager
from typing import Dict
from pathlib import Path

import sqlalchemy
import logging

from app import logger

from app.config import RESOURCES_PATH
from app.config import SAVED_VIDEOS_PATH
from app.config import BASE_IMAGES

from app.utils.exceptions import NoEventsError
from app.utils.exceptions import MultipleEventsError
from app.utils.exceptions import NoDetectionsError

from app.models import Detection
from app.models import Event
from app.models import Frame


class EventMetaData:
    def __init__(
        self, event_id: int, db_connection_string: str, logger: logging.Logger = logger
    ):
        """Helper class to retrieve metadata from database.

        Args:
            event_id (int): Corresponding database id for the event.
            db_connection_string (str): Database URI to establish connection.
        """
        self.images_path = RESOURCES_PATH / "images"
        self.videos_path = SAVED_VIDEOS_PATH
        self.logger = logger

        self.db_connection_string = db_connection_string
        Session = self.build_session(db_connection_string)
        events_session = Session()

        self.event = self.get_event_values(event_id, events_session)
        self.video_path = Path(self.event["evidence_video_path"])
        self.motion_heatmap_path = (
            Path(self.event["motion_heatmap_path"]).resolve()
            if self.event["motion_heatmap_path"] is not None
            else None
        )
        self.base_image = cv2.imread(str(BASE_IMAGES[str(self.event["camera_id"])]))

        detections_session = Session()
        self.detections = self.get_detections_values(event_id, detections_session)

    def build_session(
        self, session_connection_string: str
    ) -> sqlalchemy.orm.sessionmaker:
        """Build a Database connection session.

        Args:
            event_id (int): Corresponding database id for the event.

        Returns:
            sqlalchemy.orm.sessionmaker: DB Session initializer.
        """
        db_engine = sqlalchemy.create_engine(session_connection_string)
        session_constructor = sqlalchemy.orm.sessionmaker(bind=db_engine)
        return session_constructor

    @contextmanager
    def query_session(self, db_session):
        try:
            yield db_session
        except:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def get_event_values(self, event_id: int, db_session) -> Dict:
        """Retrieve event information from database for a given id.

        Args:
            event_id (int): Corresponding event id in database.

        Raises:
            NoEventsError: If no event is found for the given ID.
            MultipleEventsError: If many events are found for a single ID.

        Returns:
            Dict: Dictionary with the corresponding event metadata.
        """
        with self.query_session(db_session) as session:
            events_query = session.query(
                Event.timestamp,
                Event.id,
                Event.evidence_video_path,
                Event.camera_id,
                Event.motion_heatmap_path,
            ).filter(Event.id == event_id)
            query_result = events_query.all()
            if not query_result:
                raise NoEventsError(f"No event found with ID: {event_id}")
            if len(query_result) > 1:
                raise MultipleEventsError(
                    f"Unexpected multiple events retrieved: {len(query_result)}"
                )
            event = dict(query_result[0])
            return event

    def get_detections_values(self, event_id: int, db_session) -> pd.DataFrame:
        """Retrieve detections for a given event.

        Args:
            event_id (int):  Corresponding event id in database.

        Raises:
            NoDetectionsError: If no detections are found for the given event.

        Returns:
            pd.DataFrame: DataFrame with all the detections for the given event.
        """
        with self.query_session(db_session) as session:
            detections_query = (
                session.query(
                    Detection.label,
                    Detection.tracked_object_id,
                    Detection.rois,
                    Detection.x_min,
                    Detection.x_max,
                    Detection.y_min,
                    Detection.y_max,
                    Detection.event_id,
                    Detection.frame_id,
                    Frame.frame_number,
                )
                .filter(Detection.event_id == event_id)
                .filter(Detection.frame_id == Frame.id)
            )
            filtered_detections = pd.read_sql_query(
                detections_query.statement, session.bind
            )
            if len(filtered_detections) == 0:
                raise NoDetectionsError(f"No detections found for event {event_id}")
        return filtered_detections

    def update_entry(self, motion_heatmap_path: str):
        self.logger.info(f"Updating database entry to include motion heatmap")
        self.logger.info(f"Writing {str(motion_heatmap_path)}")
        Session = self.build_session(self.db_connection_string)
        update_event_session = Session()
        try:
            with self.query_session(update_event_session) as session:
                corresponding_event = (
                    session.query(Event).filter(Event.id == self.event["id"]).one()
                )
                corresponding_event.motion_heatmap_path = str(motion_heatmap_path)
                session.commit()
        except Exception as e:
            self.logger.error(f"Could not update heatmap motion entry into DB: {e}")

    def __repr__(
        self,
    ):
        return f"Event #{self.event['id']}. Saved at {self.video_path}"
