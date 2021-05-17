import copy
import logging

import cv2
import numpy as np
import pandas as pd
from pathlib import Path

from app import logger
from app.config import HEATMAP_PATH
from app.utils.exceptions import CorruptFileError
from app.utils.video import VideoReader

pd.options.mode.chained_assignment = None

FPS = 30
WINDOW_SIZE = 2


class BaseMotionHeatmap:
    def __init__(
        self,
        event_metadata: "EventMetaData",
        save_entry: bool = False,
        image_threshold: int = 2,
        max_value: int = 2,
        logger: logging.Logger = logger,
    ) -> None:
        """Base BaseMotionHeatmap class.

        This class processes a given video and overlays it's corresponding motion heatmap.
        It's based on OpenCV background substraction algorithm, to be used with cpu and GPU backends.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            save_entry (bool, optional): Wether to save heatmap calculation results. Defaults to False.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        self.event_metadata = event_metadata
        self.image_threshold = image_threshold
        self.max_value = max_value
        self.logger = logger

        self.video_reader, self.stream = self.prepare_video_reader(
            event_metadata.video_path
        )
        self.algorithm = self.prepare_extraction_algorithm()
        self.cumulative_image = self.prepare_cumulative_image(self.video_reader)

        if save_entry:
            self.logger.debug("Setting save path")
            self.save_path = Path(
                HEATMAP_PATH / f"event_{self.event_metadata.event['id']}"
            ).resolve()

        self.detections = event_metadata.detections
        self.detections[
            ["frame_number", "x_min", "y_min", "x_max", "y_max"]
        ] = self.detections[["frame_number", "x_min", "y_min", "x_max", "y_max"]].apply(
            lambda x: pd.to_numeric(x, downcast="unsigned")
        )  # FIXME detections should be saved as integers from the very beginning
        # FIXME OFFSET does not sync correctly
        self.detections["frame_number"] += FPS * WINDOW_SIZE  # Add window offset

    def __call__(
        self,
    ):
        if not self.video_reader:
            logger.warning("No video reader available")
            return
        frame_count = 0
        while self.video_reader.more():
            frame = self.video_reader.read()
            corresponding_detections = self.detections[
                self.detections.frame_number == frame_count
            ]
            processed_image = self.process(frame, corresponding_detections)
            frame_count += 1
        return processed_image

    def save_results(self, processed_image: np.ndarray) -> None:
        """Colormap and save processed heatmap, if set.

        Args:
            processed_image (np.ndarray): Processed heatmap.
        """
        colormapped = self.colormap(processed_image)
        cv2.imwrite(str(self.save_path / "heatmap.png"), colormapped)


class CPUMotionHeatmap(BaseMotionHeatmap):
    def __init__(
        self,
        detections: pd.DataFrame,
        source_path: Path,
        save_entry: bool = False,
        image_threshold: int = 2,
        max_value: int = 2,
        **video_reader_kwargs,
    ) -> None:
        """Initialize a BaseMotionHeatmap instance.

        This class processes a given video and overlays it's corresponding motion heatmap.
        It uses CPU implementation of OpenCV background substraction algorithm.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            save_entry (bool, optional): Wether to show heatmap calculation results. Defaults to False.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        super().__init__(
            detections=detections,
            source_path=source_path,
            save_entry=save_entry,
            image_threshold=image_threshold,
            max_value=max_value,
            **kwargs,
        )
        self.video_reader_kwargs = video_reader_kwargs

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
            video_reader = VideoReader(
                video_file=source_path, backend="cpu", **self.video_reader_kwargs
            ).start()
        except FileNotFoundError:
            self.logger.warning(
                f"Video file not found. Please check the file at {source_path}"
            )
            return None, None
        except CorruptFileError:
            self.logger.warning(
                f"Corrupt video. Please check the file at {source_path}"
            )
            return None, None
        frame = video_reader.read()
        self.first_frame = copy.deepcopy(frame)
        algorithm = cv2.bgsegm.createBackgroundSubtractorMOG()
        self.cumulative_image = np.zeros(
            (video_reader.height, video_reader.width), np.uint8
        )
        return video_reader, algorithm

    def process(self, frame: np.ndarray, detections: pd.DataFrame):
        grayscale_frame = cv2.cvtColor(
            frame, cv2.COLOR_BGR2GRAY
        )  # convert to grayscale
        roi_masked_frame = self.mask(grayscale_frame, detections)

        no_background_image = self.algorithm.apply(
            roi_masked_frame
        )  # remove the background
        _, thresholded_image = cv2.threshold(
            no_background_image, self.image_threshold, self.max_value, cv2.THRESH_BINARY
        )  # Remove small motion
        self.cumulative_image = cv2.add(
            self.cumulative_image, thresholded_image
        )  # Add to cumulative motion image
        return self.cumulative_image

    def mask(self, frame: np.ndarray, detections: list, mode: str = "individual"):
        base_mask = np.zeros(
            (self.video_reader.height, self.video_reader.width), dtype="uint8"
        )
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

    def colormap(self, frame: np.ndarray):
        color_image = cv2.applyColorMap(frame, cv2.COLORMAP_HOT)  # Color motion image
        overlayed_image = cv2.addWeighted(self.first_frame, 0.7, color_image, 0.7, 0)
        return overlayed_image


class GPUMotionHeatmap(BaseMotionHeatmap):
    def __init__(
        self,
        event_metadata: "EventMetaData",
        save_entry: bool = False,
        image_threshold: int = 2,
        max_value: int = 2,
        **video_reader_kwargs,
    ) -> None:
        """Initialize a GPU-based BaseMotionHeatmap instance.

        This class processes a given video and overlays it's corresponding motion heatmap.
        It's based on OpenCV background substraction algorithm.

        Args:
            detections (pd.DataFrame): Detections asociated with the video's events.
            source_path (str): Path of video to be analyzed.
            image_threshold (int): Image threshold for masking.
            max_value (int): #TODO Find out jeje
        """
        self.video_reader_kwargs = video_reader_kwargs
        super().__init__(
            event_metadata=event_metadata,
            save_entry=save_entry,
            image_threshold=image_threshold,
            max_value=max_value,
        )

    def prepare_video_reader(self, video_path: Path) -> cv2.VideoCapture:
        try:
            video_reader = VideoReader(
                video_file=video_path,
                backend="gpu",
                **self.video_reader_kwargs,
            ).start()
        except FileNotFoundError:
            self.logger.warning(
                f"Video file not found. Please check the file at {video_path}"
            )
            return None, None
        except CorruptFileError:
            self.logger.warning(f"Corrupt video. Please check the file at {video_path}")
            return None, None
        except Exception as e:
            self.logger.error(f"Unknown error while loading video reader: {e}")
        stream = cv2.cuda_Stream()
        return video_reader, stream

    def prepare_extraction_algorithm(
        self,
    ):
        try:
            algorithm = cv2.cuda.createBackgroundSubtractorMOG()
            return algorithm
        except Exception as e:
            logger.error(f"Background extraction initialization error: {e}")
            return None

    def prepare_cumulative_image(
        self,
        video_reader: VideoReader,
    ) -> cv2.cuda_GpuMat:
        """Build video handlers and cumulative image.

        Args:
            source_path (Path): Source video location

        Returns:
            [tuple]: OpenCV's video reader, video writer and background substraction.
        """
        frame = video_reader.read()
        self.first_frame = copy.deepcopy(frame.download())
        cumulative_image = cv2.cuda_GpuMat(
            np.zeros((video_reader.height, video_reader.width), np.uint8)
        )
        return cumulative_image

    def process(self, frame: cv2.cuda_GpuMat, detections: pd.DataFrame):
        grayscale_frame = cv2.cuda.cvtColor(
            frame, cv2.COLOR_BGR2GRAY
        )  # convert to grayscale
        roi_masked_frame = self.mask(grayscale_frame, detections)
        no_background_image = self.algorithm.apply(
            roi_masked_frame, learningRate=0.1, stream=self.stream
        )  # remove the background
        _, thresholded_image = cv2.cuda.threshold(
            no_background_image, self.image_threshold, self.max_value, cv2.THRESH_BINARY
        )  # Remove small motion
        self.cumulative_image = cv2.cuda.add(
            self.cumulative_image, thresholded_image
        )  # Add to cumulative motion image
        return self.cumulative_image

    def mask(self, frame: np.ndarray, detections: list, mode: str = "individual"):
        base_mask = np.zeros(
            (self.video_reader.height, self.video_reader.width), dtype="uint8"
        )
        if not len(detections) > 0:
            return cv2.cuda.bitwise_and(frame, frame, mask=cv2.cuda_GpuMat(base_mask))
        raw_masks = detections.apply(
            lambda detection: cv2.rectangle(
                base_mask,
                (detection.x_min, detection.y_min),
                (detection.x_max, detection.y_max),
                (255, 255, 255),
                -1,
            ),
            axis=1,
        )
        masks = np.stack(raw_masks)
        mask = np.maximum.reduce(masks)
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
        return cv2.cuda.bitwise_and(frame, frame, mask=cv2.cuda_GpuMat(mask))

    def colormap(self, frame: np.ndarray):
        frame = frame.download()
        color_image = cv2.applyColorMap(frame, cv2.COLORMAP_HOT)  # Color motion image
        overlayed_image = cv2.addWeighted(
            self.first_frame.download(), 0.7, color_image, 0.7, 0
        )
        return overlayed_image

    def __call__(
        self,
    ):
        processed_image = super().__call__()
        if not processed_image:
            return
        if self.save_path:
            self.event_metadata.update_entry(self.save_path.with_suffix(".npy"))
            np.save(self.save_path, processed_image.download())
            return
        return processed_image.download()


if __name__ == "__main__":
    pass
