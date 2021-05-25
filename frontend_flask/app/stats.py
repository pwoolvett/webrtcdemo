import cv2
import numpy as np
import pandas as pd
import requests
import time
import logging

from contextlib import contextmanager
from typing import Tuple
from datetime import datetime

from app import app

from app.models import Detection
from app.models import Event
from app.models import Frame
from app.models import get_session

from app.utils.heatmap import GPUMotionHeatmap
from app.utils.logger import logger


Session = get_session("sqlite:////db/test.db")

BASE_IMAGES = {
    0: cv2.imread(str(app.config["RESOURCES_PATH"] / "img" / "base_image.png")),
    1: cv2.imread(str(app.config["RESOURCES_PATH"] / "img" / "base_image.png"))
}
# TODO: configure this dynamically from database
# TODO: do not preload the images

IMAGE_SIZE = np.array(cv2.imread("base_image.png")).shape
GPU_FRACTION = 0.1


class EventStatistics:
    def __init__(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        camera_id: int,
        db_session_constructor, 
        **kwargs
    ):
        """Initialize an EventStatistics instance.

        Args:
            start_datetime (datetime): Start date and time for query.
            end_datetime (datetime): End date and time for query
            camera_id (int): Selected camera to review.
            db_session_constructor (int): Database session constructor.
        """
        self.logger = logger
        self.base_image = BASE_IMAGES[camera_id]
        self.logger.info(f"Using database constructor: {db_session_constructor}")
        self.Session = db_session_constructor
        self.images_path = app.config["RESOURCES_PATH"] / "images"
        self.videos_path = app.config["SAVED_VIDEOS_PATH"]
        self.heatmap_endpoint = app.config["HEATMAP_ENDPOINT"]
        self.events, self.detections = self.get_values(
            start_datetime, end_datetime, camera_id
        )

    @classmethod
    def build_from_form(cls, form, db_session_constructor):
        kwargs = dict(
            start_datetime=datetime.combine(form.date_from.data, form.time_from.data),
            end_datetime=datetime.combine(form.date_to.data, form.time_to.data),
            camera_id=int(form.camera_id.data),
            db_session_constructor=db_session_constructor,
        )
        return cls(**kwargs)

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

    def request_heatmaps(self, event_list:list)->bool:
        try:
            heatmap_requests = [requests.get(self.heatmap_endpoint, params={'event_id': event_id}, verify="/certs/cert.pem") for event_id in event_list]
            heatmaps_status = [ request.json()['STATUS'] for request in heatmap_requests]    
        except Exception as e:
            print("ERROR COMPUTING HEATMAPS", e)
            return 
        return all(status in ["Already computed", "Failed computation"] for status in heatmaps_status)

    def aggregate_heatmap_values(self, events_id_list:list)->np.ndarray:
        with self.query_session() as session:
            query_result = (
                session.query(Event.motion_heatmap_path)
                .filter(Event.id.in_(events_id_list))).all()
        heatmap_paths = [value[0] for value in query_result]
        heatmap = np.zeros_like(np.load(heatmap_paths[0]))
        for heatmap_path in heatmap_paths:
            heatmap_values = np.load(heatmap_path)
            heatmap += heatmap_values
        return heatmap


    def compute_heatmap_values(
        self,
    ):
        """Overlay heatmap values to image.

        Returns:
            np.array: Overlayed image.
        """
        t0 = time.perf_counter()
        event_id_list = self.events['id'].to_list()
        heatmaps_computed = self.request_heatmaps(event_id_list)
        while not heatmaps_computed:
            time.sleep(2)
            heatmaps_computed = self.request_heatmaps(event_id_list)
        heatmap_values = self.aggregate_heatmap_values(event_id_list)
        self.logger.info(f"Heatmap computation time for {len(event_id_list)} events: {time.perf_counter()-t0:.3f} s")
        return heatmap_values

    def display_heatmap(self, frame:np.ndarray):
        color_image = cv2.applyColorMap(
            frame, cv2.COLORMAP_HOT
        )  # Color motion image
        print(f"COLOR: {color_image.shape}")
        print(f"BASE: {self.base_image.shape}")
        overlayed_image = cv2.addWeighted(self.base_image, 0.7, color_image, 0.7, 0)
        save_path = self.images_path/"heatmap.png"
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
            event_count=len(self.detections.event_id.unique()),
        )

    def __call__(
        self,
    ):
        descriptive_statistics = self.get_statistics()
        heatmap_values = self.compute_heatmap_values()
        if heatmap_values is None:
            heatmap_location = str(app.config["RESOURCES_PATH"] / "images" / "base_image.png")
        else:
            heatmap_location = self.display_heatmap(heatmap_values)
        return dict(
            heatmap=heatmap_location,
            event_count=descriptive_statistics["event_count"],
            object_count=descriptive_statistics["object_count"],
        )
