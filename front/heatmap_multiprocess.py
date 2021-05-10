import time
import pandas as pd
import multiprocessing
from pathlib import Path

from app.utils.heatmap import MotionHeatmap

VIDEOS_PATH = Path("/home/rmclabs/RMCLabs/webrtcdemo/debug")


def compute(args):
    return compute_heatmap_values(*args)


def group_events(events, detections):
    for event_id in events['id'].unique():
        event = events[events.id==event_id]
        video_path = VIDEOS_PATH/str(event.evidence_video_path.values[0])
        filtered_detections = detections[detections.event_id==event_id]
        yield filtered_detections, video_path
        
def compute_heatmap_values(detections, video_path):
    t0 = time.perf_counter()
    heatmap = MotionHeatmap(detections=detections, source_path=video_path)
    heatmap_values = heatmap()
    print(f"Heatmap values computation time: {time.perf_counter()-t0:.3f} s")
    return heatmap_values

def single_process_main():
    detections = pd.read_pickle("/home/rmclabs/RMCLabs/webrtcdemo/db/selected_detections.pkl")
    events = pd.read_pickle("/home/rmclabs/RMCLabs/webrtcdemo/db/selected_events.pkl")
    grouped_events = [*group_events(events, detections)]
    filtered_detections, video_path = grouped_events[0]
    compute_heatmap_values(filtered_detections, video_path)

def multiprocess_main():
    detections = pd.read_pickle("/home/rmclabs/RMCLabs/webrtcdemo/db/selected_detections.pkl")
    events = pd.read_pickle("/home/rmclabs/RMCLabs/webrtcdemo/db/selected_events.pkl")
    grouped_events = [*group_events(events, detections)]
    with multiprocessing.Pool(processes=int(multiprocessing.cpu_count()/2)) as pool:
        heatmap_values = pool.map(compute, grouped_events)

if __name__=="__main__":
    single_process_main()
    