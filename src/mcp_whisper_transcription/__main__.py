"""Main entry point for MCP Whisper Transcription Server."""

import asyncio
from .server import app

async def async_main():
    """Run the MCP server using stdio transport."""
    await app.run()

def main():
    """Entry point for the command line script."""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
