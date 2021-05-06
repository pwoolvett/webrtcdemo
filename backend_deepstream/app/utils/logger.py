import logging
import os 

from logging import getLogger

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL)

logger = getLogger("Pythia_API")

logger.info=print
logger.debug=print
logger.error=print
logger.warn=print
logger.warning=print
logger.critical=print

logger.info(f"LOGGER LEVEL: {LOGLEVEL}")
