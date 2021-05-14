from os import stat
import cv2
import numpy as np
import pandas as pd
from contextlib import contextmanager
from typing import ContextManager, Tuple
from PIL import Image
from datetime import datetime
from pathlib import Path

from pandas.core.indexes.base import InvalidIndexError
from app import app

import ray

from app.utils.heatmap import GPUMotionHeatmap

from app.models import Detection
from app.models import Event
from app.models import Frame
from app.models import get_session

Session = get_session("sqlite:////db/test.db")

BASE_IMAGES = {
    0: cv2.imread(str(app.config["RESOURCES_PATH"] / "images" / "base_image.png"))
}
IMAGE_SIZE = np.array(cv2.imread("base_image.png")).shape
GPU_FRACTION = 0.1


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
        self.Session = Session
        self.images_path = app.config["RESOURCES_PATH"] / "images"
        self.videos_path = app.config["SAVED_VIDEOS_PATH"]
        self.events, self.detections = self.get_values(
            start_datetime, end_datetime, camera_id
        )

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

    @contextmanager
    def query_session(
        self,
    ):
        db_session = self.Session()
        try:
            yield db_session
        except:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def get_values(
        self, start_datetime: datetime, end_datetime: datetime, camera_id: int
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        with self.query_session() as session:
            events_query = (
                session.query(Event.timestamp, Event.id, Event.evidence_video_path)
                .filter(Event.timestamp <= end_datetime)
                .filter(Event.timestamp >= start_datetime)
                .filter(Event.camera_id == camera_id)
            )
            selected_events = pd.read_sql_query(events_query.statement, session.bind)
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
                .filter(Detection.event_id.in_(list(selected_events.id)))
                .filter(Detection.frame_id == Frame.id)
            )
            selected_detections = pd.read_sql_query(
                detections_query.statement, session.bind
            )
            selected_detections.to_pickle("/db/selected_detections.pkl")
            selected_events.to_pickle("/db/selected_events.pkl")
        return selected_events, selected_detections

    def create_resources(
        self,
    ):
        return {
            "heatmap": self.build_heatmap(),
            "timeline": self.build_timeline(),
            "statistics": self.build_main_statistics(),
        }

    def compute_heatmap_values(
        self,
    ):
        """Overlay heatmap values to image.

        Returns:
            np.array: Overlayed image.
        """
        import time

        results = []
        t0 = time.perf_counter()
        for video_path, detection in [*self.group_events()]:
            experiment_actor = self.compute_heatmap.remote(detection, video_path)
            results.append(experiment_actor)
        print(
            f"Heatmap computation time for {len( [*self.group_events()])} events: {time.perf_counter()-t0:.3f} s"
        )
        return results

    def display_heatmap(self, frame: np.ndarray):
        color_image = cv2.applyColorMap(frame, cv2.COLORMAP_HOT)  # Color motion image
        overlayed_image = cv2.addWeighted(self.base_image, 0.7, color_image, 0.7, 0)
        print(f"BASE: {self.base_image.shape}")
        print(f"COLOR: {color_image.shape}")
        save_path = self.images_path / "heatmap.png"
        cv2.imwrite(str(save_path), overlayed_image)
        return save_path

    def group_events(
        self,
    ):
        for event_id in self.events["id"].unique():
            event = self.events[self.events.id == event_id]
            video_path = str(
                self.videos_path / str(event.evidence_video_path.values[0])
            )
            filtered_detections = self.detections[self.detections.event_id == event_id]
            yield video_path, filtered_detections

    @staticmethod
    @ray.remote(num_gpus=GPU_FRACTION)
    def compute_heatmap(detections: pd.DataFrame, video_path: str) -> np.ndarray:
        """Compute a motion heatmap for a single event.

        Args:
            detections (pd.DataFrame): Detections DataFrame for a given event.
            video_path (pd.DataFrame): Event video path

        Returns:
            np.ndarray: Motion heatmap values, for the given event.
        """
        heatmap = GPUMotionHeatmap(
            detections=detections, source_path=video_path, maxsize=100
        )
        if not heatmap.video_reader:
            return
        heatmap_values = heatmap()
        return heatmap_values  # 1 / masked_values.max() * masked_values

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

    def __call__(
        self,
    ):
        descriptive_statistics = self.get_statistics()
        compute_references = self.compute_heatmap_values()
        heatmap_values = [
            result for result in ray.get(compute_references) if result is not None
        ]
        frame = sum(heatmap_values)
        heatmap_location = self.display_heatmap(frame)
        return dict(
            heatmap=heatmap_location,
            object_count=descriptive_statistics["object_count"],
            detection_count=descriptive_statistics["detection_count"],
        )
