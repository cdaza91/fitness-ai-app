import logging
import sys

def setup_logging():
    """Configures centralized logging for the entire FastAPI application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Optional: Customize log levels for specific third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Initialize logging configuration
setup_logging()
