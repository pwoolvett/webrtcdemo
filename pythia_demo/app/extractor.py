#!/usr/bin/env python

from pythiags import frames_per_batch
from pythiags import objects_per_frame
from pythiags import Producer
from pythiags.deepstream.iterators import analytics_per_frame
from pythiags.deepstream.iterators import analytics_per_object
from pythiags.deepstream.parsers import detector_bbox


class AnalyticsExtractor(Producer):
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
