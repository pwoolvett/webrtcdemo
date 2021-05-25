from datetime import datetime

from app import app

from app.models import Event


class EventDescription(object):
    def __init__(self, event_id: int, event: Event) -> None:
        self.id = event_id
        self.date = event.timestamp.date().strftime("%d/%m/%Y")
        self.time = event.timestamp.time().strftime("%H:%M:%S")
        self.type = event.event_type
        self.area = app.config["AREAS_PER_CAM"][event.camera_id]
        self.video_path = event.evidence_video_path

    def get_video(
        self,
    ):
        # TODO play video from
        raise NotImplementedError


class RegistryStatistics:
    def __init__(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        camera_id: int,
        db_session,
    ):
        """Initialize a RegistryStatistics instance.

        Args:
            start_datetime (datetime): Start date and time for query.
            end_datetime (datetime): End date and time for query
            camera_id (int): Selected camera to review.
            db_session (int): Database session constructor.
        """
        self.Session = db_session
        self.event_list = self.get_events(start_datetime, end_datetime, camera_id)

    @classmethod
    def build_from_form(cls, form, db_session):
        kwargs = dict(
            start_datetime=datetime.combine(form.date_from.data, form.time_from.data),
            end_datetime=datetime.combine(form.date_to.data, form.time_to.data),
            camera_id=int(form.camera_id.data),
            db_session=db_session,
        )
        return cls(**kwargs)

    def get_events(self, start_datetime, end_datetime, camera_id) -> list:
        db_session = self.Session()  # TODO Change to context manager
        events_query = (
            db_session.query(
                Event.camera_id,
                Event.timestamp,
                Event.event_type,
                Event.evidence_video_path,
            )
            .filter(Event.timestamp <= end_datetime)
            .filter(Event.timestamp >= start_datetime)
            .filter(Event.camera_id == camera_id)
        )
        return events_query.all()

    def render(
        self,
    ):
        return [
            EventDescription(event_id, event)
            for (event_id, event) in enumerate(self.event_list)
        ]
