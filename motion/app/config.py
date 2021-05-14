from pathlib import Path


def retrieve_base_images(available_cameras, images_path):
    return {
        camera: str(images_path / "base_images" / f"{camera}.png")
        for camera in available_cameras
    }


GPU_FRACTION = 0.1
DB_PATH = "/db/test.db"
RESOURCES_PATH = (Path(__file__).parent / "resources").resolve()
IMAGES_PATH = (RESOURCES_PATH / "images").resolve()
HEATMAP_PATH = Path("/heatmaps")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{str(DB_PATH)}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
AVAILABLE_CAMERAS = ["0"]  # TODO Implement cameras retrieval
BASE_IMAGES = retrieve_base_images(
    AVAILABLE_CAMERAS, IMAGES_PATH
)  # {camera:cv2.imread(str(IMAGES_PATH/"base_images"/f"{camera}.png")) for camera in AVAILABLE_CAMERAS}
SAVED_VIDEOS_PATH = Path("/videos").resolve()  # FIXME Set definitve video location
