"""Main entry point for MCP Whisper Transcription Server."""

import asyncio
from mcp.server.stdio import stdio_server
from .server import app

async def main():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
