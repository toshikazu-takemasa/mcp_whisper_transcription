"""Main entry point for MCP Whisper Transcription Server."""

import sys
import logging
from .server import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Entry point for the command line script."""
    try:
        logger.info("Starting MCP Whisper Transcription Server...")
        # FastMCP handles its own event loop internally
        app.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
