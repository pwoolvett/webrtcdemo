
import logging
from logging import RootLogger
from logging import getLogger
import os


def force_kivy_release_root_logger():
    from kivy.logger import Logger
    logging.root = RootLogger(LOGLEVEL)  # undo KIVY LOGGER taking full control

def build(name="GstBackend"):
    LOGLEVEL = getattr(logging, os.environ.get('LOGLEVEL', 'INFO').upper())
    force_kivy_release_root_logger()
    
    logging.basicConfig(
        level=LOGLEVEL,
        format='%(relativeCreated)6d %(threadName)s %(message)s'
    )
    logger = getLogger(name)

    logger.info("logger.info is active")
    logger.debug("logger.debug  is active")
    logger.error("logger.error  is active")
    logger.warning("logger.warning  is active")
    logger.critical("logger.critical  is active")

    logger.info(f"LOGGER LEVEL: {LOGLEVEL}")

    return logger

logger = build()
