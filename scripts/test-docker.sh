#!/bin/bash

# Test script for MCP Whisper Transcription Docker image

set -e

echo "🐳 Testing MCP Whisper Transcription Docker Image"
echo "================================================"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Set default values
IMAGE_NAME="ghcr.io/toshikazu-takemasa/mcp-whisper-transcription:latest"
LOCAL_IMAGE_NAME="mcp-whisper-transcription:test"

# Function to build local image
build_local() {
    echo "🔨 Building local Docker image..."
    docker build -t "$LOCAL_IMAGE_NAME" .
    echo "✅ Local image built successfully"
}

# Function to pull remote image
pull_remote() {
    echo "📥 Pulling remote Docker image..."
    docker pull "$IMAGE_NAME"
    echo "✅ Remote image pulled successfully"
}

# Function to test image
test_image() {
    local image=$1
    echo "🧪 Testing image: $image"
    
    # Check if OPENAI_API_KEY is set
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "⚠️  OPENAI_API_KEY environment variable is not set"
        echo "   The container will start but API calls will fail"
    fi
    
    # Run container in test mode
    echo "🚀 Testing container startup..."
    docker run --rm \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}" \
        "$image" \
        python -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from mcp_whisper_transcription.server import app
    print('✅ MCP Whisper Transcription server loaded successfully')
    print('📋 Available tools:')
    tools = app.list_tools()
    for tool in tools:
        print(f'  - {tool.name}: {tool.description}')
    print(f'Total tools: {len(tools)}')
except Exception as e:
    print(f'❌ Error loading server: {e}')
    sys.exit(1)
"
}

# Parse command line arguments
case "${1:-remote}" in
    "local")
        build_local
        test_image "$LOCAL_IMAGE_NAME"
        ;;
    "remote")
        pull_remote
        test_image "$IMAGE_NAME"
        ;;
    "both")
        build_local
        test_image "$LOCAL_IMAGE_NAME"
        echo ""
        pull_remote
        test_image "$IMAGE_NAME"
        ;;
    *)
        echo "Usage: $0 [local|remote|both]"
        echo "  local  - Build and test local image"
        echo "  remote - Pull and test remote image (default)"
        echo "  both   - Test both local and remote images"
        exit 1
        ;;
esac

echo ""
echo "🎉 Docker image test completed successfully!"
echo ""
echo "💡 To use the image:"
echo "   docker run -e OPENAI_API_KEY=\"your-key\" \\"
echo "     -v \$(pwd)/audio_files:/app/audio_files \\"
echo "     $IMAGE_NAME"
