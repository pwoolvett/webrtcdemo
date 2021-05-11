import time
import pandas as pd
import multiprocessing
from pathlib import Path

import ray

import line_profiler
profile = line_profiler.LineProfiler()

from app.utils.heatmap import GPUMotionHeatmap

VIDEOS_PATH = Path("/videos")

class Experiment(object):
    def __init__(self, detections_path:Path, events_path:Path, videos_path:Path=VIDEOS_PATH) -> None:
        self.videos_path = videos_path
        self.detections = pd.read_pickle(detections_path)
        self.events = pd.read_pickle(events_path)
        print(f"Found {len(self.events)} events and {len(self.detections)} detections")
    
    def compute(self, args):
        return self.compute_heatmap_values(*args)

    def group_events(self, ):
        for event_id in self.events['id'].unique():
            event = self.events[self.events.id==event_id]
            video_path = self.videos_path/str(event.evidence_video_path.values[0])
            filtered_detections = self.detections[self.detections.event_id==event_id]
            yield filtered_detections, video_path

@ray.remote(num_gpus=0.1)
def compute_heatmap_values(detections, video_path):
    heatmap = GPUMotionHeatmap(detections=detections, source_path=video_path, maxsize=100)
    heatmap_values = heatmap()
    return heatmap_values

def single_process_main(experiment, ):
    results = []
    for detection, video_path in [*experiment.group_events(experiment.events, experiment.detections)]:
        experiment_actor = Experiment.remote(detection, video_path)
        results.append(experiment_actor)
    return results
    
def multiprocess_main():
    detections = pd.read_pickle("/db/selected_detections.pkl")
    events = pd.read_pickle("/db/selected_events.pkl")
    print(f"Found {len(events)} events and {len(detections)} detections")
    grouped_events = [*group_events(events, detections)]
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count()/8)) as pool:
        heatmap_values = pool.map(compute, grouped_events)
    

def ray_main(actors, experiment):
    from ray.util import ActorPool
    pool = ActorPool(actors)
    results = pool.map(experiment.compute_heatmap_values, [*experiment.group_events(experiment.events, experiment.detections)])
    return results

if __name__=="__main__":
    ray.init()
    
    videos_path = Path("/videos")
    detections_path = Path("/db/selected_detections.pkl")
    events_path = Path("/db/selected_events.pkl")

    results = []
    
    experiment = Experiment(detections_path,events_path,videos_path)
    
    t0 = time.perf_counter()
    
    for detection, video_path in [*experiment.group_events()]:
        
        # heatmap = GPUMotionHeatmap(detections=detection, source_path=video_path, maxsize=300)
        # heatmap()
        experiment_actor = compute_heatmap_values.remote(detection, video_path)
        results.append(experiment_actor)
    ray.get(results)
    print(f"Experiments took: {time.perf_counter()-t0:.3f} s")
    heatmap = GPUMotionHeatmap(detections=detection, source_path=video_path, maxsize=100)
    import cProfile
    cProfile.run('heatmap()', 'ray.gpu')
    ray.shutdown()
    