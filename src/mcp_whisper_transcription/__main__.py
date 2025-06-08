"""Main entry point for MCP Whisper Transcription Server."""

import asyncio
import sys
from .server import app


async def async_main():
    """Async entry point."""
    # Run the MCP server in stdio mode
    await app.run_stdio_async()


def main():
    """Entry point for the command line script."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
