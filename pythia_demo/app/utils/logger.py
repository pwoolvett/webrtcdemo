import logging
import os 

from logging import getLogger

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL)

logger = getLogger("Pythia_API")
logger.info(f"LOGGER LEVEL: {LOGLEVEL}")