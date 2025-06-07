"""Tests for the MCP Whisper Transcription Server."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_whisper_transcription.server import (
    get_audio_file_support,
    TRANSCRIBE_AUDIO_FORMATS,
    ENHANCEMENT_PROMPTS,
)


class TestAudioFileSupport:
    """Test audio file support detection."""

    @pytest.mark.asyncio
    async def test_supported_audio_format(self):
        """Test that supported audio formats are detected correctly."""
        # Create a mock file path
        mock_path = Mock(spec=Path)
        mock_path.suffix.lower.return_value = ".mp3"
        mock_path.stat.return_value = Mock(st_mtime=1234567890, st_size=1024000)
        
        with patch('mcp_whisper_transcription.server.AudioSegment') as mock_audio:
            mock_audio.from_file.return_value = Mock(__len__=lambda x: 30000)  # 30 seconds
            
            result = await get_audio_file_support(mock_path)
            
            assert result.format == "mp3"
            assert result.transcription_support is not None
            assert "whisper-1" in result.transcription_support
            assert result.chat_support is not None
            assert result.duration_seconds == 30.0

    @pytest.mark.asyncio
    async def test_unsupported_audio_format(self):
        """Test that unsupported audio formats are detected correctly."""
        mock_path = Mock(spec=Path)
        mock_path.suffix.lower.return_value = ".txt"
        mock_path.stat.return_value = Mock(st_mtime=1234567890, st_size=1024)
        
        result = await get_audio_file_support(mock_path)
        
        assert result.format == "txt"
        assert result.transcription_support is None
        assert result.chat_support is None


class TestConstants:
    """Test constants and configurations."""

    def test_transcribe_audio_formats(self):
        """Test that audio formats are properly defined."""
        assert ".mp3" in TRANSCRIBE_AUDIO_FORMATS
        assert ".wav" in TRANSCRIBE_AUDIO_FORMATS
        assert ".flac" in TRANSCRIBE_AUDIO_FORMATS
        assert ".m4a" in TRANSCRIBE_AUDIO_FORMATS

    def test_enhancement_prompts(self):
        """Test that enhancement prompts are properly defined."""
        assert "detailed" in ENHANCEMENT_PROMPTS
        assert "storytelling" in ENHANCEMENT_PROMPTS
        assert "professional" in ENHANCEMENT_PROMPTS
        assert "analytical" in ENHANCEMENT_PROMPTS
        
        # Check that all prompts are non-empty strings
        for prompt_type, prompt_text in ENHANCEMENT_PROMPTS.items():
            assert isinstance(prompt_text, str)
            assert len(prompt_text) > 0


class TestServerImport:
    """Test that the server can be imported correctly."""

    def test_import_server(self):
        """Test that the server module can be imported."""
        from mcp_whisper_transcription.server import app
        assert app is not None

    def test_import_package(self):
        """Test that the package can be imported."""
        from mcp_whisper_transcription import app
        assert app is not None
