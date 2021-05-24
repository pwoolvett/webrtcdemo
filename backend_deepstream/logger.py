import logging
# from logging import RootLogger
# from logging import getLogger
import os

from kivy.logger import Logger
# def force_kivy_release_root_logger(root_log_level):
#     from kivy.logger import Logger
#     Logger.setLevel(LOG_LEVELS["debug"])
    # logging.root = RootLogger(root_log_level)  # undo KIVY LOGGER taking full control


def build(name="GstBackend"):
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    # logging.basicConfig(
    #     level=LOGLEVEL, format="%(relativeCreated)6d %(threadName)s %(message)s"
    # )
    # force_kivy_release_root_logger(root_log_level=LOGLEVEL)

    # logging.basicConfig(
    #     level=LOGLEVEL, format="%(relativeCreated)6d %(threadName)s %(message)s"
    # )
    Logger.setLevel(LOGLEVEL)
    # logger = getLogger(name)
    logger = Logger

    logger.critical("logger.critical  is active")
    logger.error("logger.error  is active")
    logger.warning("logger.warning  is active")
    logger.info("logger.info is active")
    logger.debug("logger.debug  is active")

    logger.info(f"LOGGER LEVEL: {LOGLEVEL}")

    return logger


logger = build()
