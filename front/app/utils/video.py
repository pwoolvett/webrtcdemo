import time
import cv2
from threading import Thread
from queue import Queue
from pathlib import Path


from app.utils.logger import logger

class VideoReader:
    def __init__(self, video_file: Path, maxsize: int=500, backend: str="cpu") -> None:
        if not backend.lower() in ['cpu', 'gpu']:
            raise ValueError(f"{backend} not supported. Please select between cpu and gpu")
        self.backend = backend.lower()
        self.video_stream = self.setup(str(video_file))
        self.queue = Queue(maxsize=maxsize)
        self.stopped = False
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.logger = logger
    
    def setup(self, video_path:str)->cv2.VideoCapture:
        """Check wether the video stream is corrupt and initialize video stream and properties.

        Args:
            video_path (str): Video location.

        Returns:
            cv2.VideoCapture: Video streamer.
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"No video found at {video_path}")
        test_video_streamer = cv2.VideoCapture(video_path)
        opened_video, _ = test_video_streamer.read()
        if not opened_video:
            raise ValueError(f"Could not open video at {video_path}. Corrupt file")

        #Set relevant video properties
        self.height = int(test_video_streamer.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.width = int(test_video_streamer.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.fps = int(test_video_streamer.get(cv2.CAP_PROP_FPS))
        self.frame_number = int(test_video_streamer.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.debug(f"Video details: ({self.width}x{self.height}). {self.frame_number} frames")
        #Cleanup to avoid losing first frame
        test_video_streamer.release()
        return cv2.VideoCapture(video_path)

    def start(self):
        """
        Start video processing.    
        """
        self.thread.start()
        return self
    
    def update(self):
        """
        Retrieve a new frame (if possible) or close the video stream.
        """
        while True:
            if self.stopped:
                break
            ret, frame = self.video_stream.read()
            if not ret:
                self.stopped = True
                break
            if self.backend == "gpu":
                frame = cv2.cuda_GpuMat(frame)
            self.queue.put(frame, timeout=None)
        self.video_stream.release()
    
    def read(self):
        """
        Retrieve a frame from video frames queue.
        """
        return self.queue.get()
    
    def running(self):
        """
        
        """
        return self.more() or not self.stopped
    
    def more(self):
        """
        Yield video frames.
        """
        tries = 0
        while self.queue.qsize() == 0 and not self.stopped and tries <20:
            time.sleep(0.1)
            tries += 1
        return self.queue.qsize() > 0
    
    def stop(self):
        """
        Stop stream.
        """
        self.stopped = True
        self.thread.join()
