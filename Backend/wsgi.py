# Standard library imports
import configparser
import sys

# Third-party imports
from waitress import serve

# Local/application imports
from app import app
from utility.logger import get_logger
logger = get_logger()


config = configparser.ConfigParser()
config.read('configuration.ini')

# Get server configurations with fallback values
host = config.get("Server", "host", fallback="0.0.0.0")
port = config.get("Server", "port", fallback=11040)
threads = config.get("Server", "threads", fallback=2)

if __name__ == "__main__":
    try:
        logger.info("Starting Application in production mode with Waitress")
        logger.info(f"Startin Waitress server on {host}:{port} with {threads} threads")
        
        # Start the server
        serve(
            app,
            host=host,
            port=int(port),
            threads=int(threads)
        )
    except Exception as e:
        logger.error(f"Fatal error during application startup: {str(e)}")
        sys.exit(1)
    finally:
        try:
            logger.info("Cleaning up resources")
            pass
        except Exception as e:
            logger.error(f"Error during final cleanup: {str(e)}")
            sys.exit(1)
