"""
Voice Transcription API using OpenAI Whisper

This module handles audio file transcription using Whisper's tiny model
optimized for low-memory environments like Render's free tier.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import whisper
import tempfile
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Global model instance (loaded once at startup)
model = None

def load_whisper_model():
    """Load Whisper model on startup"""
    global model
    try:
        logger.info("Loading Whisper tiny model...")
        model = whisper.load_model("tiny")  # Only ~75MB RAM usage
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        model = None

# Load model when module is imported
load_whisper_model()

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Transcribe audio file to text using Whisper
    
    Args:
        file: Audio file (webm, wav, mp3, etc.)
        
    Returns:
        Dict with transcribed text or error message
    """
    if model is None:
        raise HTTPException(
            status_code=503, 
            detail="Whisper model not available. Please try again later."
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an audio file."
        )
    
    # Limit file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB."
        )
    
    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(content)
            temp_file_path = temp_audio.name
        
        logger.info(f"Transcribing audio file: {file.filename} ({len(content)} bytes)")
        
        # Transcribe using Whisper
        result = model.transcribe(
            temp_file_path,
            language="en",  # Force English for better performance
            task="transcribe"
        )
        
        transcribed_text = result['text'].strip()
        logger.info(f"Transcription successful: '{transcribed_text[:100]}...'")
        
        return {
            "text": transcribed_text,
            "confidence": result.get('segments', [{}])[0].get('no_speech_prob', 0.0) if result.get('segments') else 0.0,
            "language": result.get('language', 'en')
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
        
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file: {e}")

@router.get("/transcribe/health")
async def transcribe_health():
    """Health check for transcription service"""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "model_loaded": model is not None,
        "model_name": "whisper-tiny"
    }
