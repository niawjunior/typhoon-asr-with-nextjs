from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import os
import time
from typing import Dict, List, Optional
import uvicorn
from openai import OpenAI
import shutil

# Try to import typhoon_asr, but don't fail if it's not available
try:
    from typhoon_asr import transcribe as typhoon_transcribe
    TYPHOON_PACKAGE_AVAILABLE = True
except ImportError:
    TYPHOON_PACKAGE_AVAILABLE = False

app = FastAPI(
    title="Typhoon ASR API",
    description="API for Thai speech recognition using Typhoon ASR",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    return {"message": "Typhoon ASR API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    api_key: str = Form(None),
    use_api: bool = Form(True),
    with_timestamps: bool = Form(False),
    device: str = Form("auto")
):
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        # Copy the uploaded file to the temporary file
        shutil.copyfileobj(file.file, tmp_file)
        audio_path = tmp_file.name
    
    try:
        # Choose transcription method based on mode
        if use_api:
            if not api_key:
                raise HTTPException(status_code=400, detail="API key is required for API mode")
            result = transcribe_with_api(
                audio_path,
                api_key,
                with_timestamps=with_timestamps
            )
        else:  # Local model
            if not TYPHOON_PACKAGE_AVAILABLE:
                raise HTTPException(status_code=400, detail="typhoon-asr package is not installed")
            result = transcribe_with_local_model(
                audio_path,
                device=device,
                with_timestamps=with_timestamps
            )
        
        # Check for errors
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        try:
            os.unlink(audio_path)
        except:
            pass

# Function to transcribe audio using API
def transcribe_with_api(audio_path: str, api_key: str, with_timestamps: bool = False) -> Dict:
    client = OpenAI(
        base_url="https://api.opentyphoon.ai/v1",
        api_key=api_key
    )
    
    start_time = time.time()
    
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="typhoon-asr-realtime",
            file=audio_file
        )
    
    processing_time = time.time() - start_time
    
    # Parse the response
    result = {
        "text": response.text,
        "processing_time": processing_time,
    }
    
    # If timestamps were requested but not available in the API response,
    # we'll return an empty list
    if with_timestamps:
        result["timestamps"] = []
    
    return result

# Function to transcribe audio using local model
def transcribe_with_local_model(audio_path: str, device: str = "auto", with_timestamps: bool = False) -> Dict:
    if not TYPHOON_PACKAGE_AVAILABLE:
        return {"error": "typhoon-asr package is not installed"}
    
    try:
        result = typhoon_transcribe(
            audio_path,
            model_name="scb10x/typhoon-asr-realtime",
            with_timestamps=with_timestamps,
            device=device
        )
        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
