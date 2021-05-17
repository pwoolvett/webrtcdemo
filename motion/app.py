#!/usr/bin/env python
import numpy as np

import ray
from ray import serve

from app import logger
from app.config import SQLALCHEMY_DATABASE_URI
from app.utils.exceptions import NoEventsError, MultipleEventsError, NoDetectionsError
from app.utils.metadata import EventMetaData
from app.utils.heatmap import GPUMotionHeatmap
from app.utils.heatmap import CPUMotionHeatmap

client = serve.start(http_host="0.0.0.0", http_port=3333)


@serve.deployment(route_prefix="/heatmap")
class MotionHeatmap:
    def __init__(self):
        self.count = 0
        self.computing = {}
        self.failed = {}
        self.logger = logger
        self.connection_string = SQLALCHEMY_DATABASE_URI

    def __call__(self, request):
        event_id = request.query_params["event_id"]
        event_metadata = EventMetaData(event_id, self.connection_string)

        # Check that the event´s ID heatmap has not been computed succesfully.
        if event_metadata.motion_heatmap_path:
            # If it has been already computed, remove from computing state
            computing_event = self.computing.get(event_id, None)
            if computing_event:
                self.computing.pop(event_id)
            return {
                "STATUS": "Already computed",
                "heatmap_location": str(event_metadata.motion_heatmap_path),
            }

        # Check that the event´s ID heatmap has not failed to be computed.
        failed_event = self.failed.get(event_id, None)
        if failed_event:
            return {"STATUS": "Failed computation", "failure": str(failed_event)}

        # Check that the event´s ID heatmap is not being computed already.
        computing_event = self.computing.get(event_id, None)
        if computing_event:
            return {
                "STATUS": "Already Computing",
                "compute_reference": str(computing_event),
            }

        # Compute
        try:
            object_ref = compute_heatmap.remote(event_metadata)
            self.computing[event_id] = object_ref
            return {
                "STATUS": "Starting Computing",
                "compute_reference": str(object_ref),
            }

        except (NoEventsError, MultipleEventsError, NoDetectionsError) as exception:
            self.logger.exception(exception)
            self.failed[event_id] = str(exception)
            return {"STATUS": "Failed computation", "failure": f"{type(exception)}"}

    def register_computation(
        self,
    ):  # TODO Add locking mechanism for failure and computing
        raise NotImplementedError


@ray.remote(num_gpus=0.5)
def compute_heatmap(
    event_metadata: "EventMetaData", backend: str = "gpu", **kwargs
) -> np.ndarray:
    """Compute a motion heatmap for a single event.

    Args:
        event_data (EventData): Event metadata description.
        backend (str): Wether to use CPU or GPU for heatmap computation.

    Returns:
        np.ndarray: Motion heatmap values for the given event.
    """
    if backend.lower() == "gpu":
        heatmap = GPUMotionHeatmap(
            event_metadata=event_metadata, save_entry=True, maxsize=100
        )
    elif backend.lower() == "cpu":
        heatmap = CPUMotionHeatmap(
            event_metadata=event_metadata, save_entry=True, maxsize=100
        )
    else:
        raise ValueError(
            f"{backend} is not supported. Please select between 'cpu' and 'gpu'."
        )
    if not heatmap.video_reader:
        return
    heatmap()


if __name__ == "__main__":
    MotionHeatmap.deploy()
    import time

    while True:
        time.sleep(5)
