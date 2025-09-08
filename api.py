from fastapi import FastAPI, File, UploadFile, HTTPException, Form, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import tempfile
import os
import time
import json
import asyncio
from typing import Dict, List, Optional, Any, Generator
import uvicorn
from openai import OpenAI
import shutil
import wave
import numpy as np

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
    expose_headers=["*"],  # Expose all headers
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

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: Dict):
        await websocket.send_json(data)

manager = ConnectionManager()

# WebSocket endpoint for real-time streaming transcription
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    print("WebSocket connection attempt received")
    audio_path = None
    interim_path = None
    
    try:
        await manager.connect(websocket)
        print("WebSocket connected successfully")
        
        # Initial setup message
        await manager.send_json(websocket, {"status": "connected", "message": "Ready for audio streaming"})
        
        # Create a temporary file for audio chunks
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            audio_path = tmp_file.name
        
        # Initialize variables for audio processing
        audio_chunks = []
        sample_rate = 16000  # Default sample rate
        channels = 1  # Mono
        sample_width = 2  # 16-bit
        
        # Default configuration
        api_key = ""
        use_api = True
        device = "auto"
        with_timestamps = False
        
        # Process incoming messages
        while True:
            try:
                data = await websocket.receive_bytes()
                
                # Try to decode as text (for JSON control messages)
                try:
                    text_data = data.decode('utf-8')
                    print(f"Received text data: {text_data[:100]}...")
                    
                    try:
                        control_message = json.loads(text_data)
                        message_type = control_message.get("type")
                        
                        if message_type == "config":
                            # Get configuration parameters
                            api_key = control_message.get("api_key", "")
                            use_api = control_message.get("use_api", True)
                            device = control_message.get("device", "auto")
                            with_timestamps = control_message.get("with_timestamps", False)
                            
                            print(f"Config received: use_api={use_api}, device={device}")
                            await manager.send_json(websocket, {"status": "config_received"})
                            
                        elif message_type == "end":
                            print("End message received, processing complete audio")
                            if audio_chunks:
                                # Process complete audio
                                with wave.open(audio_path, "wb") as wav_file:
                                    wav_file.setnchannels(channels)
                                    wav_file.setsampwidth(sample_width)
                                    wav_file.setframerate(sample_rate)
                                    wav_file.writeframes(b''.join(audio_chunks))
                                
                                if use_api:
                                    if not api_key:
                                        await manager.send_json(websocket, {"status": "error", "message": "API key is required for API mode"})
                                    else:
                                        result = transcribe_with_api(audio_path, api_key, with_timestamps=with_timestamps)
                                        await manager.send_json(websocket, {"status": "complete", "result": result})
                                else:  # Local model
                                    if not TYPHOON_PACKAGE_AVAILABLE:
                                        await manager.send_json(websocket, {"status": "error", "message": "typhoon-asr package is not installed"})
                                    else:
                                        result = transcribe_with_local_model(audio_path, device=device, with_timestamps=with_timestamps)
                                        await manager.send_json(websocket, {"status": "complete", "result": result})
                            break  # Exit the loop after processing
                            
                        else:
                            print(f"Unknown message type: {message_type}")
                            await manager.send_json(websocket, {"status": "error", "message": f"Unknown message type: {message_type}"})
                    
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        await manager.send_json(websocket, {"status": "error", "message": f"Invalid JSON: {str(e)}"})
                
                except UnicodeDecodeError:
                    # Binary audio data
                    audio_chunks.append(data)
                    await manager.send_json(websocket, {"status": "chunk_received", "chunks": len(audio_chunks)})
                    
                    # Process interim audio every 10 chunks
                    if len(audio_chunks) % 10 == 0:
                        print(f"Processing interim audio ({len(audio_chunks)} chunks)")
                        try:
                            # Create temporary file for interim processing
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                interim_path = tmp.name
                            
                            # Write current chunks to WAV
                            with wave.open(interim_path, "wb") as wav_file:
                                wav_file.setnchannels(channels)
                                wav_file.setsampwidth(sample_width)
                                wav_file.setframerate(sample_rate)
                                wav_file.writeframes(b''.join(audio_chunks))
                            
                            # Process interim audio
                            if use_api and api_key:
                                result = transcribe_with_api(interim_path, api_key, with_timestamps=False)
                                await manager.send_json(websocket, {"status": "interim", "result": result})
                            elif not use_api and TYPHOON_PACKAGE_AVAILABLE:
                                result = transcribe_with_local_model(interim_path, device=device, with_timestamps=False)
                                await manager.send_json(websocket, {"status": "interim", "result": result})
                        
                        except Exception as e:
                            print(f"Error processing interim audio: {e}")
                        
                        finally:
                            # Clean up interim file
                            if interim_path and os.path.exists(interim_path):
                                try:
                                    os.unlink(interim_path)
                                    interim_path = None
                                except:
                                    pass
            
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
                
            except Exception as e:
                print(f"Error in WebSocket loop: {e}")
                await manager.send_json(websocket, {"status": "error", "message": f"Server error: {str(e)}"})
    
    except WebSocketDisconnect:
        print("WebSocket disconnected during setup")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await manager.send_json(websocket, {"status": "error", "message": str(e)})
        except:
            pass
    
    finally:
        # Clean up resources
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass
                
        if interim_path and os.path.exists(interim_path):
            try:
                os.unlink(interim_path)
            except:
                pass
                
        # Disconnect from manager
        try:
            manager.disconnect(websocket)
            print("WebSocket connection closed")
        except:
            pass

# Generator function for streaming transcription
def stream_transcription(audio_path: str, api_key: str = None, use_api: bool = True, 
                       device: str = "auto", with_timestamps: bool = False) -> Generator[str, None, None]:
    """Stream transcription results as they become available."""
    try:
        # Initial message
        yield json.dumps({"status": "processing", "message": "Processing audio..."}) + "\n"
        
        # Process audio file
        if use_api:
            if not api_key:
                yield json.dumps({"status": "error", "message": "API key is required for API mode"}) + "\n"
                return
            
            # Process with API in chunks to simulate streaming
            # For real streaming, you would process audio in chunks and yield results as they come
            result = transcribe_with_api(audio_path, api_key, with_timestamps=with_timestamps)
            
            # Simulate streaming by yielding partial results
            if "text" in result:
                text = result["text"]
                words = text.split()
                
                # Stream words one by one with a small delay
                for i in range(0, len(words), 3):  # Send 3 words at a time
                    chunk = " ".join(words[i:i+3])
                    yield json.dumps({"status": "interim", "text": chunk}) + "\n"
                    time.sleep(0.2)  # Small delay to simulate real-time processing
                
                # Send final result
                yield json.dumps({"status": "complete", "result": result}) + "\n"
            else:
                yield json.dumps({"status": "error", "message": "No transcription result"}) + "\n"
        else:  # Local model
            if not TYPHOON_PACKAGE_AVAILABLE:
                yield json.dumps({"status": "error", "message": "typhoon-asr package is not installed"}) + "\n"
                return
            
            result = transcribe_with_local_model(audio_path, device=device, with_timestamps=with_timestamps)
            
            # Simulate streaming by yielding partial results
            if "text" in result:
                text = result["text"]
                words = text.split()
                
                # Stream words one by one with a small delay
                for i in range(0, len(words), 3):  # Send 3 words at a time
                    chunk = " ".join(words[i:i+3])
                    yield json.dumps({"status": "interim", "text": chunk}) + "\n"
                    time.sleep(0.2)  # Small delay to simulate real-time processing
                
                # Send final result
                yield json.dumps({"status": "complete", "result": result}) + "\n"
            else:
                yield json.dumps({"status": "error", "message": "No transcription result"}) + "\n"
    
    except Exception as e:
        yield json.dumps({"status": "error", "message": str(e)}) + "\n"
    
    finally:
        # Clean up
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass

# HTTP streaming endpoint for real-time transcription
@app.post("/stream-transcribe")
async def stream_transcribe(file: UploadFile = File(...),
                         api_key: str = Form(None),
                         use_api: bool = Form(True),
                         with_timestamps: bool = Form(False),
                         device: str = Form("auto")):
    """Stream transcription results using HTTP streaming response."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        # Copy the uploaded file to the temporary file
        shutil.copyfileobj(file.file, tmp_file)
        audio_path = tmp_file.name
    
    # Return a streaming response
    return StreamingResponse(
        stream_transcription(audio_path, api_key, use_api, device, with_timestamps),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
