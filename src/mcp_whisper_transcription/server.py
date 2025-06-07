"""Whisper MCP server core code."""

import asyncio
import base64
import os
import re
import time
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

from mcp.server import FastMCP
from openai import AsyncOpenAI
from openai.types import AudioModel, AudioResponseFormat
from openai.types.audio.speech_model import SpeechModel
from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam
from pydantic import BaseModel, Field
from pydub import AudioSegment  # type: ignore

# Type definitions for transcription
SupportedChatWithAudioFormat = Literal["mp3", "wav"]
AudioChatModel = Literal["gpt-4o-audio-preview-2024-10-01", "gpt-4o-audio-preview-2024-12-17", "gpt-4o-mini-audio-preview-2024-12-17"]
EnhancementType = Literal["detailed", "storytelling", "professional", "analytical"]
TTSVoice = Literal["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]

# Constants for checks
TRANSCRIBE_AUDIO_FORMATS = {
    ".flac",  # Added FLAC support
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".ogg",  # Added OGG support
}

# Enhancement prompts
ENHANCEMENT_PROMPTS: dict[EnhancementType, str] = {
    "detailed": "The following is a detailed transcript that includes all verbal and non-verbal elements. "
    "Background noises are noted in [brackets]. Speech characteristics like [pause], [laughs], and [sighs] "
    "are preserved. Filler words like 'um', 'uh', 'like', 'you know' are included. "
    "Hello... [deep breath] Let me explain what I mean by that. [background noise] You know, it's like...",
    "storytelling": "The following is a natural conversation with proper punctuation and flow. "
    "Each speaker's words are captured in a paragraph with emotional context preserved. "
    "Hello! I'm excited to share this story with you. It began on a warm summer morning...",
    "professional": "The following is a clear, professional transcript with proper capitalization and punctuation. "
    "Each sentence is complete and properly structured. Technical terms and acronyms are preserved exactly. "
    "The model will try to match the style and formatting of your prompt.",
    "analytical": "The following is a precise technical transcript that preserves speech patterns and terminology. "
    "Note changes in speaking pace, emphasis, and technical terms exactly as spoken. "
    "Preserve specialized vocabulary, acronyms, and technical jargon with high fidelity. "
    "Example: The API endpoint /v1/completions [spoken slowly] accepts JSON payloads "
    "with a maximum token count of 4096 [emphasis on numbers].",
}


class BaseInputPath(BaseModel):
    """Base file path input."""

    input_file_path: Path = Field(description="Path to the input audio file to process")


class BaseAudioInputParams(BaseInputPath):
    output_file_path: Optional[Path] = Field(
        default=None,
        description="Optional custom path for the output file. "
        "If not provided, defaults to input_file_path with appropriate extension",
    )


class ConvertAudioInputParams(BaseAudioInputParams):
    """Params for converting audio to mp3."""

    target_format: SupportedChatWithAudioFormat = Field(
        default="mp3", description="Target audio format to convert to (mp3 or wav)"
    )


class CompressAudioInputParams(BaseAudioInputParams):
    """Params for compressing audio."""

    max_mb: int = Field(
        default=25, gt=0, description="Maximum file size in MB. Files larger than this will be compressed"
    )


class TranscribeAudioInputParamsBase(BaseInputPath):
    response_format: AudioResponseFormat = Field(
        "text",
        description="The response format of the transcription model. "
        'Use "verbose_json" with "model"="whisper-1" for timestamps. '
        '"gpt-4o-transcribe" and "gpt-4o-mini-transcribe" only support "text" and "json".',
    )
    timestamp_granularities: list[Literal["word", "segment"]] | None = Field(
        None,
        description="""The timestamp granularities to populate for this transcription.
        `response_format` must be set `verbose_json` to use timestamp granularities.
        Either or both of these options are supported: `word`, or `segment`.
        Note: There is no additional latency for segment timestamps, but generating word timestamp incurs additional latency.
        """,
    )


class TranscribeAudioInputParams(TranscribeAudioInputParamsBase):
    """Params for transcribing audio with audio-to-text model."""

    prompt: str | None = Field(
        None,
        description="""An optional prompt to guide the transcription model's output. Effective prompts can:

        1. Correct specific words/acronyms: Include technical terms or names that might be misrecognized
        Example: "Umm, let me think like, hmm... Okay, here's what I'm thinking"

        2. Provide context: Include background information that might help with accuracy
        Example: "This is a technical presentation about machine learning algorithms."

        3. Specify speaker information: Include names or roles if multiple speakers
        Example: "The speakers are Dr. Smith and Professor Johnson discussing research."

        4. Preserve filler words: Include example with verbal hesitations
        Example: "Umm, let me think like, hmm... Okay, here's what I'm thinking"

        5. Set writing style: Use examples in desired format (simplified/traditional, formal/casual)
        Example: "The presentation is on the financial results. Our KPIs show significant growth."

        The model will try to match the style and formatting of your prompt.""",
    )


class ChatWithAudioInputParams(BaseInputPath):
    """Params for transcribing audio with LLM using custom prompt."""

    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt to use.")
    user_prompt: Optional[str] = Field(default=None, description="Custom user prompt to use.")
    model: AudioChatModel = Field(
        default="gpt-4o-audio-preview-2024-12-17", description="The audio LLM model to use for transcription"
    )


class TranscribeWithEnhancementInputParams(TranscribeAudioInputParamsBase):
    """Params for transcribing audio with LLM using template prompt."""

    enhancement_type: EnhancementType = Field(
        default="detailed", description="The enhancement type to apply to the transcription"
    )

    def to_transcribe_audio_input_params(self) -> TranscribeAudioInputParams:
        """Transfer audio with LLM using custom prompt."""
        return TranscribeAudioInputParams(
            input_file_path=self.input_file_path,
            prompt=ENHANCEMENT_PROMPTS[self.enhancement_type],
            timestamp_granularities=self.timestamp_granularities,
            response_format=self.response_format,
        )


class CreateClaudecastInputParams(BaseModel):
    """Params for text-to-speech using OpenAI's API."""

    text_prompt: str = Field(description="Text to convert to speech")
    output_file_path: Optional[Path] = Field(
        default=None, description="Output file path (defaults to speech.mp3 in current directory)"
    )
    model: SpeechModel = Field(
        default="tts-1", description="TTS model to use. tts-1 is always preferred."
    )
    voice: TTSVoice = Field(
        default="nova",
        description="Voice for the TTS (options: alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer)",
    )
    speed: float = Field(
        default=1.0,
        gt=0.25,
        lt=4.0,
        description="Speed of the speech conversion. Use if the user prompts slow or fast speech.",
    )

    model_config = {"arbitrary_types_allowed": True}


class FilePathSupportParams(BaseModel):
    """Params for checking if a file at a path supports transcription."""

    file_path: Path = Field(description="Path to the audio file")
    transcription_support: Optional[list[AudioModel]] | None = Field(
        default=None, description="List of transcription models that support this file format"
    )
    chat_support: Optional[list[AudioChatModel]] | None = Field(
        default=None, description="List of audio LLM models that support this file format"
    )
    modified_time: float = Field(description="Last modified timestamp of the file (Unix time)")
    size_bytes: int = Field(description="Size of the file in bytes")
    format: str = Field(description="Audio format of the file (e.g., 'mp3', 'wav')")
    duration_seconds: Optional[float] = Field(
        default=None, description="Duration of the audio file in seconds, if available"
    )


def check_and_get_audio_path() -> Path:
    """Check if the audio path environment variable is set and exists."""
    audio_path_str = os.getenv("AUDIO_FILES_PATH")
    if not audio_path_str:
        raise ValueError("AUDIO_FILES_PATH environment variable not set")

    audio_path = Path(audio_path_str).resolve()
    if not audio_path.exists():
        raise ValueError(f"Audio path does not exist: {audio_path}")
    return audio_path


async def get_audio_file_support(file_path: Path) -> FilePathSupportParams:
    """Determine audio transcription file format support and metadata.

    Includes file size, format, and duration information where available.
    """
    file_ext = file_path.suffix.lower()

    transcription_support: list[AudioModel] | None = (
        ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"] if file_ext in TRANSCRIBE_AUDIO_FORMATS else None
    )

    chat_support: Optional[List[str]] = (
        ["gpt-4o-audio-preview-2024-10-01", "gpt-4o-audio-preview-2024-12-17", "gpt-4o-mini-audio-preview-2024-12-17"] if file_ext in [".mp3", ".wav"] else None
    )

    # Get file metadata
    stat = file_path.stat()
    modified_time = stat.st_mtime
    size_bytes = stat.st_size

    # Try to get duration using pydub
    duration_seconds = None
    try:
        audio = AudioSegment.from_file(str(file_path))
        duration_seconds = len(audio) / 1000.0  # Convert milliseconds to seconds
    except Exception:
        # If pydub fails, we'll just leave duration as None
        pass

    return FilePathSupportParams(
        file_path=file_path,
        transcription_support=transcription_support,
        chat_support=chat_support,
        modified_time=modified_time,
        size_bytes=size_bytes,
        format=file_ext[1:],  # Remove the dot
        duration_seconds=duration_seconds,
    )


# Initialize FastMCP server
app = FastMCP("Whisper Transcription")


@app.tool()
async def transcribe_audio(params: TranscribeAudioInputParams) -> str:
    """Transcribe audio file using OpenAI Whisper API."""
    client = AsyncOpenAI()
    
    # Check if file exists
    if not params.input_file_path.exists():
        raise ValueError(f"Audio file not found: {params.input_file_path}")
    
    # Check file format support
    file_support = await get_audio_file_support(params.input_file_path)
    if not file_support.transcription_support:
        raise ValueError(f"File format {file_support.format} is not supported for transcription")
    
    try:
        with open(params.input_file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format=params.response_format,
                prompt=params.prompt,
                timestamp_granularities=params.timestamp_granularities,
            )
        
        if params.response_format == "text":
            return transcript.text
        else:
            return transcript.model_dump_json(indent=2)
            
    except Exception as e:
        raise ValueError(f"Transcription failed: {str(e)}")


@app.tool()
async def transcribe_with_enhancement(params: TranscribeWithEnhancementInputParams) -> str:
    """Transcribe audio with enhancement using predefined prompts."""
    transcribe_params = params.to_transcribe_audio_input_params()
    return await transcribe_audio(transcribe_params)


@app.tool()
async def chat_with_audio(params: ChatWithAudioInputParams) -> str:
    """Transcribe and analyze audio using OpenAI's audio-capable models."""
    client = AsyncOpenAI()
    
    # Check if file exists
    if not params.input_file_path.exists():
        raise ValueError(f"Audio file not found: {params.input_file_path}")
    
    # Check file format support
    file_support = await get_audio_file_support(params.input_file_path)
    if not file_support.chat_support:
        raise ValueError(f"File format {file_support.format} is not supported for audio chat")
    
    try:
        # Read and encode audio file
        with open(params.input_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Prepare messages
        messages: List[ChatCompletionMessageParam] = []
        
        if params.system_prompt:
            messages.append({
                "role": "system",
                "content": params.system_prompt
            })
        
        # User message with audio
        user_content: List[ChatCompletionContentPartParam] = [
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_base64,
                    "format": file_support.format
                }
            }
        ]
        
        if params.user_prompt:
            user_content.append({
                "type": "text",
                "text": params.user_prompt
            })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Make API call
        response = await client.chat.completions.create(
            model=params.model,
            messages=messages,
            modalities=["text", "audio"]
        )
        
        return response.choices[0].message.content or "No response generated"
        
    except Exception as e:
        raise ValueError(f"Audio chat failed: {str(e)}")


@app.tool()
async def convert_audio(params: ConvertAudioInputParams) -> str:
    """Convert audio file to specified format."""
    if not params.input_file_path.exists():
        raise ValueError(f"Audio file not found: {params.input_file_path}")
    
    try:
        # Load audio file
        audio = AudioSegment.from_file(str(params.input_file_path))
        
        # Determine output path
        if params.output_file_path:
            output_path = params.output_file_path
        else:
            output_path = params.input_file_path.with_suffix(f".{params.target_format}")
        
        # Export in target format
        audio.export(str(output_path), format=params.target_format)
        
        return f"Audio converted successfully to {output_path}"
        
    except Exception as e:
        raise ValueError(f"Audio conversion failed: {str(e)}")


@app.tool()
async def compress_audio(params: CompressAudioInputParams) -> str:
    """Compress audio file to reduce file size."""
    if not params.input_file_path.exists():
        raise ValueError(f"Audio file not found: {params.input_file_path}")
    
    try:
        # Check current file size
        current_size_mb = params.input_file_path.stat().st_size / (1024 * 1024)
        
        if current_size_mb <= params.max_mb:
            return f"File is already under {params.max_mb}MB ({current_size_mb:.2f}MB). No compression needed."
        
        # Load audio file
        audio = AudioSegment.from_file(str(params.input_file_path))
        
        # Determine output path
        if params.output_file_path:
            output_path = params.output_file_path
        else:
            output_path = params.input_file_path.with_name(
                f"{params.input_file_path.stem}_compressed{params.input_file_path.suffix}"
            )
        
        # Calculate compression ratio needed
        target_size_bytes = params.max_mb * 1024 * 1024
        current_size_bytes = params.input_file_path.stat().st_size
        compression_ratio = target_size_bytes / current_size_bytes
        
        # Reduce bitrate to achieve target size
        bitrate = f"{int(128 * compression_ratio)}k"
        
        # Export compressed audio
        audio.export(str(output_path), format="mp3", bitrate=bitrate)
        
        new_size_mb = output_path.stat().st_size / (1024 * 1024)
        
        return f"Audio compressed from {current_size_mb:.2f}MB to {new_size_mb:.2f}MB. Saved to {output_path}"
        
    except Exception as e:
        raise ValueError(f"Audio compression failed: {str(e)}")


@app.tool()
async def get_file_support(params: FilePathSupportParams) -> str:
    """Check if a file supports transcription and get file metadata."""
    if not params.file_path.exists():
        raise ValueError(f"File not found: {params.file_path}")
    
    file_support = await get_audio_file_support(params.file_path)
    
    result = {
        "file_path": str(file_support.file_path),
        "format": file_support.format,
        "size_mb": round(file_support.size_bytes / (1024 * 1024), 2),
        "duration_seconds": file_support.duration_seconds,
        "transcription_support": file_support.transcription_support,
        "chat_support": file_support.chat_support,
        "modified_time": time.ctime(file_support.modified_time)
    }
    
    return f"File information:\n{result}"


@app.tool()
async def create_speech(params: CreateClaudecastInputParams) -> str:
    """Convert text to speech using OpenAI's TTS API."""
    client = AsyncOpenAI()
    
    try:
        # Determine output path
        if params.output_file_path:
            output_path = params.output_file_path
        else:
            output_path = Path("speech.mp3")
        
        # Make TTS API call
        response = await client.audio.speech.create(
            model=params.model,
            voice=params.voice,
            input=params.text_prompt,
            speed=params.speed
        )
        
        # Save audio file
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return f"Speech generated successfully and saved to {output_path}"
        
    except Exception as e:
        raise ValueError(f"Speech generation failed: {str(e)}")
