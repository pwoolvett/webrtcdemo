import copy
import logging

import cv2
import numpy as np
from pathlib import Path
import pandas as pd

from app.utils.video import VideoReader
from app.utils.logger import logger
from app.utils.exceptions import CorruptFileError

pd.options.mode.chained_assignment = None

FPS = 30
WINDOW_SIZE = 2

class MotionHeatmap:
    def __init__(
        self,
        detections: pd.DataFrame,
        source_path: Path,
        save_path: Path = None,
        debug: bool = False,
        image_threshold: int = 2,
        max_value: int = 2,
        logger: logging.Logger=logger
    ) -> None:
        """Base MotionHeatmap class.

        This object processes a given video and overlays it's corresponding motion heatmap.
        It's based on OpenCV background substraction algorithm, to be used with cpu and GPU backends.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            save_path (str, optional): Resulting heatmap save path. If None is provided, heatmap is not saved.
            debug (bool, optional): Wether to show intermediate representations of the heatmap calculation. Defaults to False.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        self.detections = detections
        self.detections[["frame_number", "x_min", "y_min", "x_max", "y_max"]] = self.detections[["frame_number", "x_min", "y_min", "x_max", "y_max"]].apply(lambda x: pd.to_numeric(x, downcast='unsigned'))  # FIXME detections should be saved as integers from the very beginning
            #FIXME OFFSET does not sync correctly
        self.detections["frame_number"] += FPS * WINDOW_SIZE  # Add window offset
        
        self.debug = debug
        self.image_threshold = image_threshold
        self.max_value = max_value
        self.logger = logger
        
        if save_path:
            self.save_path = Path(save_path).resolve()
    
    def __call__(
        self,
    ):
        frame_count = 0
        while self.video_reader.more():
            frame = self.video_reader.read()
            corresponding_detections = self.detections[
                self.detections.frame_number == frame_count
            ]
            processed_image = self.process(
                frame, corresponding_detections, frame_count
            )
            frame_count += 1
        if hasattr(self, 'save_path'):
            x = self.colormap(processed_image)
            cv2.imwrite(str(self.save_path / "heatmap.png"), x)
        return processed_image

    def save_results(self, processed_image:np.ndarray)-> None:
        """Colormap and save processed heatmap, if set.

        Args:
            processed_image (np.ndarray): Processed heatmap.
        """
        if hasattr(self, 'save_path'):
            colormapped = self.colormap(processed_image)
            cv2.imwrite(str(self.save_path / "heatmap.png"), colormapped)


class CPUMotionHeatmap(MotionHeatmap):
    def __init__(
        self,
        detections: pd.DataFrame,
        source_path: Path,
        save_path: Path = None,
        debug: bool = False,
        image_threshold: int = 2,
        max_value: int = 2,
        **video_reader_kwargs
    ) -> None:
        """Initialize a MotionHeatmap instance.

        This class processes a given video and overlays it's corresponding motion heatmap.
        It uses CPU implementation of OpenCV background substraction algorithm.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            save_path (str, optional): Resulting heatmap save path. If None is provided, heatmap is not saved.
            debug (bool, optional): Wether to show intermediate representations of the heatmap calculation. Defaults to False.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        super().__init__(detections=detections, source_path=source_path, save_path=save_path, debug=debug, image_threshold=image_threshold, max_value=max_value, **kwargs)
        self.video_reader_kwargs = video_reader_kwargs
        self.video_reader, self.substractor = self.setup(Path(source_path).resolve())

    def setup(
        self,
        source_path: str,
    ):
        """Build video handlers and cumulative image.

        Args:
            source_path (Path): Source video location

        Returns:
            [tuple]: OpenCV's video reader, video writer and background substraction.
        """
        try:
            video_reader = VideoReader(video_file=source_path, backend="cpu", **self.video_reader_kwargs).start()
        except FileNotFoundError:
            self.logger.warning(f"Video file not found. Please check the file at {source_path}")
            return None, None
        except CorruptFileError:
            self.logger.warning(f"Corrupt video. Please check the file at {source_path}")
            return None, None
        frame = video_reader.read()
        self.first_frame = copy.deepcopy(frame)
        substractor = cv2.bgsegm.createBackgroundSubtractorMOG()
        self.cumulative_image = np.zeros((video_reader.height, video_reader.width), np.uint8)
        return video_reader, substractor


    def process(self, frame: np.ndarray, detections: pd.DataFrame, idx: int):
        grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # convert to grayscale
        roi_masked_frame = self.mask(grayscale_frame, detections)

        no_background_image = self.substractor.apply(
            roi_masked_frame
        )  # remove the background
        _, thresholded_image = cv2.threshold(
            no_background_image, self.image_threshold, self.max_value, cv2.THRESH_BINARY
        )  # Remove small motion
        self.cumulative_image = cv2.add(
            self.cumulative_image, thresholded_image
        )  # Add to cumulative motion image
        
        if self.debug:
            cv2.imwrite(
                f"{self.save_video_location}/thresholded/{idx:04d}.jpg",
                thresholded_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/thresholded/{idx:04d}.jpg",
                thresholded_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/background/{idx:04d}.jpg",
                no_background_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/masked/{idx:04d}.jpg", roi_masked_frame
            )
            cv2.imwrite(
                f"{self.save_video_location}/cumulative/{idx:04d}.jpg",
                self.cumulative_image,
            )
        return self.cumulative_image

    def mask(self, frame: np.ndarray, detections: list, mode: str = "individual"):
        base_mask = np.zeros((self.video_reader.height, self.video_reader.width), dtype="uint8")
        if mode.lower() == "individual":
            masks = []
            if len(detections) == 0:
                mask = base_mask
            for _, detection in detections.iterrows():
                mask = cv2.rectangle(
                    base_mask,
                    (detection.x_min, detection.y_min),
                    (detection.x_max, detection.y_max),
                    (255, 255, 255),
                    -1,
                )
                masks.append(mask)
            if len(masks) > 1:  # Reduce masks
                mask = sum(masks)
        elif mode.lower() == "group":
            mask = cv2.rectangle(
                base_mask,
                (detections.x_min.min(), detections.y_min.min()),
                (detections.x_max.max(), detections.y_max.max()),
                (255, 255, 255),
                -1,
            )
        frame = cv2.bitwise_and(frame, frame, mask=mask)
        return frame

    def colormap(self, frame:np.ndarray):
        color_image = cv2.applyColorMap(
            frame, cv2.COLORMAP_HOT
        )  # Color motion image
        overlayed_image = cv2.addWeighted(self.first_frame, 0.7, color_image, 0.7, 0)
        return overlayed_image


class GPUMotionHeatmap(MotionHeatmap):
    def __init__(
        self,
        detections: pd.DataFrame,
        source_path: Path,
        save_path: Path = None,
        debug: bool = False,
        image_threshold: int = 2,
        max_value: int = 2, 
        **video_reader_kwargs
    ) -> None:
        """Initialize a MotionHeatmap instance.

        This class processes a given video and overlays it's corresponding motion heatmap.
        It's based on OpenCV background substraction algorithm.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            save_path (str, optional): Resulting heatmap save path. If None is provided, heatmap is not saved.
            debug (bool, optional): Wether to show intermediate representations of the heatmap calculation. Defaults to False.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        super().__init__(detections=detections, source_path=source_path, save_path=save_path, debug=debug, image_threshold=image_threshold, max_value=max_value)
        self.video_reader_kwargs = video_reader_kwargs
        self.video_reader, self.substractor = self.setup(Path(source_path).resolve())

    def setup(
        self,
        source_path: str,
    ):
        """Build video handlers and cumulative image.

        Args:
            source_path (Path): Source video location

        Returns:
            [tuple]: OpenCV's video reader, video writer and background substraction.
        """
        try:
            video_reader = VideoReader(video_file=source_path, backend="gpu", **self.video_reader_kwargs).start()
        except FileNotFoundError:
            self.logger.warning(f"Video file not found. Please check the file at {source_path}")
            return None, None
        except CorruptFileError:
            self.logger.warning(f"Corrupt video. Please check the file at {source_path}")
            return None, None
        frame = video_reader.read()
        self.stream = cv2.cuda_Stream()
        self.first_frame = copy.deepcopy(frame.download())
        substractor = cv2.cuda.createBackgroundSubtractorMOG()
        self.cumulative_image = cv2.cuda_GpuMat(np.zeros((video_reader.height, video_reader.width), np.uint8))
        return video_reader, substractor
        
        
    def process(self, frame: np.ndarray, detections: pd.DataFrame, idx: int):
        grayscale_frame = cv2.cuda.cvtColor(frame, cv2.COLOR_BGR2GRAY)# convert to grayscale
        
        roi_masked_frame = self.mask(grayscale_frame, detections) 

        no_background_image = self.substractor.apply(
            roi_masked_frame,
            learningRate=0.1, 
            stream=self.stream
        )  # remove the background
        _, thresholded_image = cv2.cuda.threshold(
            no_background_image, self.image_threshold, self.max_value, cv2.THRESH_BINARY
        )  # Remove small motion
        self.cumulative_image = cv2.cuda.add(
            self.cumulative_image, thresholded_image
        )  # Add to cumulative motion image
        
        if self.debug:
            cv2.imwrite(
                f"{self.save_video_location}/thresholded/{idx:04d}.jpg",
                thresholded_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/thresholded/{idx:04d}.jpg",
                thresholded_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/background/{idx:04d}.jpg",
                no_background_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/masked/{idx:04d}.jpg", roi_masked_frame
            )
            cv2.imwrite(
                f"{self.save_video_location}/cumulative/{idx:04d}.jpg",
                self.cumulative_image,
            )
            cv2.imwrite(
                f"{self.save_video_location}/overlayed/{idx:04d}.jpg", overlayed_image
            )
        return self.cumulative_image

    def mask(self, frame: np.ndarray, detections: list, mode: str = "individual"):
        base_mask = np.zeros((self.video_reader.height, self.video_reader.width), dtype="uint8")
        if not len(detections)>0:
            return cv2.cuda.bitwise_and(frame, frame, mask=cv2.cuda_GpuMat(base_mask))
        raw_masks = detections.apply(lambda detection: cv2.rectangle(base_mask,(detection.x_min, detection.y_min),(detection.x_max, detection.y_max),(255, 255, 255),-1,), axis=1)
        masks = np.stack(raw_masks)
        mask = np.maximum.reduce(masks)
        if mode.lower() == "individual":
            masks = []
            if len(detections) == 0:
                mask = base_mask
            for _, detection in detections.iterrows():
                mask = cv2.rectangle(base_mask,(detection.x_min, detection.y_min),(detection.x_max, detection.y_max),(255, 255, 255),-1,)
                masks.append(mask)
            if len(masks) > 1:  # Reduce masks
                mask = sum(masks)
        elif mode.lower() == "group":
            mask = cv2.rectangle(
                base_mask,
                (detections.x_min.min(), detections.y_min.min()),
                (detections.x_max.max(), detections.y_max.max()),
                (255, 255, 255),
                -1,
            )
        return cv2.cuda.bitwise_and(frame, frame, mask=cv2.cuda_GpuMat(mask))

    def colormap(self, frame:np.ndarray):
        frame = frame.download()
        color_image = cv2.applyColorMap(
            frame, cv2.COLORMAP_HOT
        )  # Color motion image
        overlayed_image = cv2.addWeighted(self.first_frame.download(), 0.7, color_image, 0.7, 0)
        return overlayed_image

    def __call__(self):
        processed_image = super().__call__()
        return processed_image.download()


if __name__ == "__main__":
    all_detections = pd.read_pickle(
        "/home/rmclabs/RMCLabs/webrtcdemo/db/selected_detections.pkl"
    )
    all_events = pd.read_pickle(
        "/home/rmclabs/RMCLabs/webrtcdemo/db/selected_events.pkl"
    )
    event_id = 10
    detections = all_detections[all_detections.event_id == event_id]
    video_path = f"/home/rmclabs/RMCLabs/webrtcdemo/debug/{str(all_events[all_events.id==event_id].evidence_video_path.values[0])}"
    
    heatmap = MotionHeatmap(
        source_path=Path(video_path).resolve(),
        save_path=Path("/home/rmclabs/RMCLabs/webrtcdemo/debug/heatmap"),
        detections=detections,
        debug=False,
    )
    heatmap()