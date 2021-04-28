#!/usr/bin/env python

import json
from datetime import datetime

from models import Detection
from models import Event
from models import Frame

SELECTED_ROIS = {"RF"}


def check_detection_importance(detection: dict, selected_rois: list) -> bool:
    if detection["label"].lower() != "person":
        return False
    if len(detection["objects"]) < 1:
        return False
    for obj in detection["objects"]:
        if any(x in selected_rois for x in obj["roiStatus"]):
            return True
    return False


def register_detection(detection, rois: dict, event_id: str) -> Detection:
    return Detection(
        label=detection["label"],
        confidence=detection["confidence"],
        x_min=detection["bbox"].x_min,
        x_max=detection["bbox"].x_max,
        y_min=detection["bbox"].y_min,
        y_max=detection["bbox"].y_max,
        tracked_object_id=str(detection["tracked_object_id"]),
        rois=json.dumps(rois),
        event_id=event_id,
    )


def register_frame(frame_metadata, source_id, frame_number, detections):
    return Frame(
        roi_object_count=json.dumps(
            [frame_meta["objInROIcnt"] for frame_meta in frame_metadata]
        ),
        total_object_count=json.dumps(
            [frame_meta["objCnt"] for frame_meta in frame_metadata]
        ),
        camera_id=source_id,
        frame_number=frame_number,
        detections=detections,
    )


def register_event(video_path: str, camera_id:int, event_type: str, db_session):
    event = db_session.query(
        Event
    ).filter(
        Event.evidence_video_path == video_path
    ).first()

    if not event:
        event = Event(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            evidence_video_path=video_path,
            camera_id=camera_id
        )
        db_session.add(event)
        db_session.commit()
    
    return event.id

    
if __name__ == "__main__":
    pass
