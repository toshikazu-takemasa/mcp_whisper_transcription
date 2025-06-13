#!/bin/bash

# Debug script for MCP Whisper Transcription Server

echo "=== MCP Whisper Transcription Server Debug ==="
echo "Timestamp: $(date)"
echo

# Check environment variables
echo "=== Environment Variables ==="
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..." # Show only first 10 chars for security
echo "AUDIO_FILES_PATH: $AUDIO_FILES_PATH"
echo

# Check if required directories exist
echo "=== Directory Check ==="
if [ -d "$AUDIO_FILES_PATH" ]; then
    echo "✓ Audio files directory exists: $AUDIO_FILES_PATH"
    echo "  Contents: $(ls -la "$AUDIO_FILES_PATH" 2>/dev/null | wc -l) items"
else
    echo "✗ Audio files directory missing: $AUDIO_FILES_PATH"
fi

if [ -d "/app/output" ]; then
    echo "✓ Output directory exists: /app/output"
else
    echo "✗ Output directory missing: /app/output"
fi
echo

# Test Python imports
echo "=== Python Import Test ==="
python -c "
try:
    import sys
    sys.path.insert(0, '/app/src')
    from mcp_whisper_transcription.server import app
    print('✓ Server imports successfully')
    print(f'✓ FastMCP app created: {type(app)}')
except Exception as e:
    print(f'✗ Import failed: {e}')
    sys.exit(1)
"
echo

# Test server startup (with timeout)
echo "=== Server Startup Test ==="
echo "Testing server startup (will timeout after 10 seconds)..."

timeout 10s python -c "
import sys
import os
sys.path.insert(0, '/app/src')

# Set required environment variables if not set
if not os.getenv('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = 'test-key'
if not os.getenv('AUDIO_FILES_PATH'):
    os.environ['AUDIO_FILES_PATH'] = '/app/audio_files'

try:
    from mcp_whisper_transcription.__main__ import main
    print('✓ Main function imported successfully')
    print('Starting server (will be terminated by timeout)...')
    main()
except KeyboardInterrupt:
    print('✓ Server started and responded to interrupt correctly')
except Exception as e:
    print(f'✗ Server startup failed: {e}')
    sys.exit(1)
" 2>&1

echo
echo "=== Debug Complete ==="
