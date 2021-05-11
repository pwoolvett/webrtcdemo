import logging
import os

from logging import getLogger

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL)

logger = getLogger("Pythia_API")

logger.setLevel(logging.DEBUG)
logger.setLevel(getattr(logging, LOGLEVEL))  # tTODO: use this instead

logger.info(f"LOGGER LEVEL: {LOGLEVEL}")

