#!/usr/bin/env python

import json
from datetime import datetime

from models import Detection
from models import Event
from models import Frame
from models import Object


def dump_metadata(meta:dict, db_session):
    frames = []
    for (source_id, frame_number), full_metadata in meta.items():
        frame_metadata = full_metadata['analytics']
        detection_metadata = full_metadata['detections']
        detections = []
        for detection in detection_metadata:
            objects = []    
            for obj in detection['objects']:
                objects.append(Object(
                    rois = str(obj['roiStatus']),
                )
                ) 
            detections.append(
                Detection(
                label=detection["label"],
                confidence=detection["confidence"],
                x_min=detection["bbox"].x_min,
                x_max=detection["bbox"].x_max,
                y_min=detection["bbox"].y_min,
                y_max=detection["bbox"].y_max,
                objects = objects
            )
            )
        event, object_count = check_event(frame_metadata)
        frame = Frame(
                object_count = object_count,
                camera_id = source_id,
                frame_number = frame_number,
                detections = detections, 
                )
        db_session.add(frame)
        frames.append(frame)
        if event:
            event_time = datetime.utcnow()
            event = Event(
                timestamp = event_time,
                event_type = "Trespassing",
                evidence_video_path = f"TBD_{event_time}",
                frames = frame,
            ) 
            db_session.add(event)      
    db_session.commit()
    return frames

def check_event(frame_metadata):
    object_count = sum(sum(frame_meta["objCnt"].values()) for frame_meta in frame_metadata)
    has_event = sum(sum(frame_meta["objInROIcnt"].values()) for frame_meta in frame_metadata) > 0
    return has_event, object_count

if __name__=='__main__':
    pass