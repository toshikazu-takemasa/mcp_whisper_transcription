"""Main entry point for MCP Whisper Transcription Server."""

from .server import app


def main():
    """Entry point for the command line script."""
    app.run()


if __name__ == "__main__":
    main()
