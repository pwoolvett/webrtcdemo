
import os

from kivy.logger import Logger
from kivy.logger import LOG_LEVELS

logger=Logger

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').lower()
logger.setLevel(LOG_LEVELS[LOGLEVEL])


logger.info("logger.info is active")
logger.debug("logger.debug  is active")
logger.error("logger.error  is active")
logger.warning("logger.warning  is active")
logger.critical("logger.critical  is active")

logger.info(f"LOGGER LEVEL: {LOGLEVEL}")


# import os
# import logging
# from logging import getLogger

# def build(name="Pythia_API"):
#     LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
#     logging.basicConfig(
#         level=LOGLEVEL,
#         format='%(relativeCreated)6d %(threadName)s %(message)s'
#     )
#     logger = getLogger(name)

#     logger.info("logger.info")
#     logger.debug("logger.debug")
#     logger.error("logger.error")
#     logger.warn("logger.warn")
#     logger.warning("logger.warning")
#     logger.critical("logger.critical")

#     logger.info(f"LOGGER LEVEL: {LOGLEVEL}")
#     return logger

# logger = build()
