#!/usr/bin/env python

import random

from pythiags import frames_per_batch, objects_per_frame, Producer, Consumer
from pythiags.deepstream.iterators import analytics_per_frame
from pythiags.deepstream.iterators import object_analytics_per_frame
from pythiags.deepstream.iterators import analytics_per_object
from pythiags.deepstream.parsers import detector_bbox

from common import Session
from dump import check_detection_importance
from dump import register_detection
from dump import register_frame
from dump import register_event
from dump import SELECTED_ROIS


class VideoRecorder:
    def __init__(self, *a, **kw):
        self.ctr = 0

    def record(self):
        if random.randint(0,1):
            self.ctr += random.randint(0,100)
        return f"/tmp/videos/{self.ctr}.avi"


class MyCustomExtract(Producer):
    def extract_metadata(self, pad, info):
        meta = {}
        for frame_metadata in frames_per_batch(info):
            key = (frame_metadata.source_id, frame_metadata.frame_num)
            filtered_frame_analytics = []
            for frame_analytics in analytics_per_frame(frame_metadata):
                filtered_frame_analytics.append(
                    {
                        "objCnt": frame_analytics.objCnt,
                        "objInROIcnt": frame_analytics.objInROIcnt,
                        "objLCCumCnt": frame_analytics.objLCCumCnt,
                        "objLCCurrCnt": frame_analytics.objLCCurrCnt,
                        "ocStatus": frame_analytics.ocStatus,
                        "unique_id": frame_analytics.unique_id,
                    }
                )
            detection_count = 0
            detection_metadata = []
            for obj_meta in objects_per_frame(frame_metadata):
                object_data = []
                object_count = 0
                # First we need to retrieve all objects for a given detection
                for obj_analytics in analytics_per_object(obj_meta):
                    object_count += 1
                    object_analytics = {
                        "lcStatus": obj_analytics.lcStatus,
                        "dirStatus": obj_analytics.dirStatus,
                        "ocStatus": obj_analytics.ocStatus,
                        "roiStatus": obj_analytics.roiStatus,
                        "source_id": frame_metadata.source_id,
                        "frame_num": frame_metadata.frame_num,
                    }
                    object_data.append(object_analytics)
                detection_count += 1
                detection = {
                    "tracked_object_id": obj_meta.object_id,
                    "label": obj_meta.obj_label,
                    "confidence": obj_meta.confidence,
                    "frame_number": frame_metadata.frame_num,
                    "bbox": detector_bbox(obj_meta),
                    "objects": object_data,
                }
                detection_metadata.append(detection)
            meta[key] = {
                "analytics": filtered_frame_analytics,
                "detections": detection_metadata,
            }
        return meta


class DDBBWriterProcess(Consumer):
    def __init__(self, ):
        self.video_recorder = VideoRecorder()
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

            # Check if event has already been registered
            event_id = register_event(video_path, event_type="Trespassing", db_session=db_session)

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
