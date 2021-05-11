#!/usr/bin/env python

from pythiags import Consumer

from app.utils.logger import logger
from app.utils.common import Session
from app.utils.dump import check_detection_importance
from app.utils.dump import register_detection
from app.utils.dump import register_frame
from app.utils.dump import register_event
from app.utils.dump import SELECTED_ROIS


class DDBBWriter(Consumer):
    def __init__(
        self,
    ):
        self.video_recorder = None
        self.selected_rois = SELECTED_ROIS
        self.Session = Session

    def dump_metadata(self, meta: dict, db_session):
        for (source_id, frame_number), full_metadata in meta.items():
            frame_metadata = full_metadata["analytics"]
            detection_metadata = full_metadata["detections"]

            important_detections = self.filter_detections(detection_metadata)

            if not len(important_detections):
                return

            video_path = self.video_recorder.record()
            logger.info(f"Saving video at {video_path}")

            # Check if event has already been registered
            event_id = register_event(
                video_path,
                event_type="Trespassing",
                db_session=db_session,
                camera_id=source_id,
            )

            registered_detections = []
            for detection in important_detections:
                rois = []
                for obj in detection["objects"]:
                    rois.extend(obj["roiStatus"])
                registered_detection = register_detection(detection, rois, event_id)
                registered_detections.append(registered_detection)

            registered_frame = register_frame(
                frame_metadata, source_id, frame_number, registered_detections
            )
            db_session.add(registered_frame)
        db_session.commit()

    def filter_detections(self, detections: list) -> list:
        # TODO use yield here instead
        important_detections = []
        for detection in detections:
            if not check_detection_importance(detection, self.selected_rois):
                continue
            important_detections.append(detection)
        return important_detections

    def incoming(self, events):
        session = self.Session()
        self.dump_metadata(events, session)

    def set_video_recorder(self, video_recorder):
        self.video_recorder = video_recorder
