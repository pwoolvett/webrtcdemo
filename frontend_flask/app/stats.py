import cv2
import numpy as np
import pandas as pd
from typing import Tuple
from PIL import Image
from datetime import datetime
from pathlib import Path
from app import app

from app.models import Detection
from app.models import Event
from app.models import get_session

Session = get_session("sqlite:///test.db")

db_session = Session()

datetime_from = datetime(2021, 4, 23, 17, 14, 0)
datetime_to = datetime(2021, 4, 23, 17, 20, 0)

BASE_IMAGES = {
    0: Image.open(app.config["RESOURCES_PATH"] / "images" / "base_image.png")
}
IMAGE_SIZE = np.array(cv2.imread("base_image.png")).shape


class EventStatistics:
    def __init__(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        camera_id: int,
        db_session,
    ):
        """Initialize an EventStatistics instance.

        Args:
            start_datetime (datetime): Start date and time for query.
            end_datetime (datetime): End date and time for query
            camera_id (int): Selected camera to review.
            db_session (int): Database session constructor.
        """
        self.base_image = BASE_IMAGES[camera_id]
        self.Session = db_session
        self.images_path = app.config["RESOURCES_PATH"] / "images"
        self.events, self.detections = self.get_values(
            start_datetime, end_datetime, camera_id
        )
        self.descriptive_statistics = self.get_statistics()
        self.heatmap_location = self.build_heatmap()

    @classmethod
    def build_from_form(cls, form, db_session):
        kwargs = dict(
            start_datetime=datetime.combine(form.date_from.data, form.time_from.data),
            end_datetime=datetime.combine(form.date_to.data, form.time_to.data),
            camera_id=int(form.camera_id.data),
            db_session=db_session,
        )
        return cls(**kwargs)

    def mask(self, bbox: np.array) -> np.array:
        mask = np.zeros(self.base_image.size)
        x_min, x_max, y_min, y_max = bbox
        mask[x_min:x_max, y_min:y_max] += 1
        return mask

    def get_values(
        self, start_datetime: datetime, end_datetime: datetime, camera_id: int
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        db_session = self.Session()
        events_query = (
            db_session.query(Event.timestamp, Event.id)
            .filter(Event.timestamp <= end_datetime)
            .filter(Event.timestamp >= start_datetime)
            .filter(Event.camera_id == camera_id)
        )
        selected_events = pd.read_sql_query(events_query.statement, db_session.bind)
        db_session = self.Session()  # TODO Change to context manager
        detections_query = db_session.query(
            Detection.tracked_object_id,
            Detection.rois,
            Detection.x_min,
            Detection.x_max,
            Detection.y_min,
            Detection.y_max,
            Detection.event_id,
        ).filter(Detection.event_id.in_(list(selected_events.id)))
        selected_detections = pd.read_sql_query(
            detections_query.statement, db_session.bind
        )
        return selected_events, selected_detections

    def create_resources(
        self,
    ):
        return {
            "heatmap": self.build_heatmap(),
            "timeline": self.build_timeline(),
            "statistics": self.build_main_statistics(),
        }

    def build_heatmap(
        self,
    ):
        """Overlay heatmap values to image.

        Returns:
            np.array: Overlayed image.
        """
        heatmap_values = self.compute_heatmap_values()
        heatmap_base = None
        normalized_heatmap = cv2.normalize(
            heatmap_values.T,
            heatmap_base,
            alpha=0,
            beta=255,
            norm_type=cv2.NORM_MINMAX,
            dtype=cv2.CV_8U,
        )
        base_image = cv2.cvtColor(np.array(self.base_image), cv2.COLOR_RGB2BGR)
        heatmap = cv2.applyColorMap(normalized_heatmap, cv2.COLORMAP_JET)
        overlayed_image = cv2.addWeighted(heatmap, 0.7, base_image, 0.3, 0)
        heatmap_path = self.images_path / "heatmap.png"
        cv2.imwrite(str(heatmap_path), overlayed_image)
        return str(heatmap_path)

    def compute_heatmap_values(
        self,
    ) -> pd.DataFrame:
        masked_values = (
            self.detections[["x_min", "x_max", "y_min", "y_max"]]
            .astype("int")
            .apply(self.mask, axis=1)
            .sum()
        )
        return 1 / masked_values.max() * masked_values

    def build_timeline(self, frequency: str = "1min"):
        """Group events for timeline display.

        Args:
            frequency (str): Binning frequency.

        Returns:
            list: Grouped events DataFrame, by 1-min bins.
        """
        return self.events.groupby(
            [pd.Grouper(key="timestamp", freq=frequency)]
        ).count()

    def get_statistics(
        self,
    ) -> dict:
        """Compute descriptive statistics for a given event set.

        Returns:
            dict: Number of objects.
        """
        return dict(
            object_count=len(self.detections.tracked_object_id.value_counts()),
            detection_count=len(self.detections),
        )

    def render(
        self,
    ):
        return dict(
            heatmap=self.heatmap_location,
            object_count=self.descriptive_statistics["object_count"],
            detection_count=self.descriptive_statistics["detection_count"],
        )
