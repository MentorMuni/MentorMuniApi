import logging
import sys

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to stdout for Railway
    ]
)

logger = logging.getLogger("mentormuni")
logger.info("Logging is configured for production.")