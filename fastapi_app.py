from fastapi import FastAPI, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
import shutil
import uuid
from fastapi.responses import JSONResponse
from fastapi import Request

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
app.mount("/static", StaticFiles(directory="day-1/static"), name="static")

# Templates setup
templates = Jinja2Templates(directory="day-1/templates")

# Environment variables
MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

ASSEMBLY_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ASSEMBLY_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLY_TRANSCRIBE_URL = "https://api.assemblyai.com/v2/transcript"

# Data model
class InputText(BaseModel):
    text: str

# Serve homepage
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Generate audio from text
@app.post("/generate-audio/")
async def generate_audio(input_text: InputText):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="MURF_API_KEY not found")

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "voice_id": "en-IN-aarav",
        "text": input_text.text.strip(),
        "output_format": "mp3",
        "style": "Conversational"
    }

    try:
        response = requests.post(MURF_API_URL, json=payload, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Murf API request failed: {str(e)}")

    data = response.json()
    audio_url = data.get("audioFile")

    if not audio_url:
        raise HTTPException(status_code=400, detail="No audio URL returned")

    return {"audio_url": audio_url}

# Upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": os.path.getsize(file_location)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Day 7: Echo Bot v2 - Transcribe & Murf TTS
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    if not ASSEMBLY_API_KEY:
        raise HTTPException(status_code=500, detail="ASSEMBLY_API_KEY not found")
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="MURF_API_KEY not found")

    # Save uploaded audio
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Upload to AssemblyAI
    headers = {"authorization": ASSEMBLY_API_KEY}
    with open(temp_path, "rb") as f:
        upload_res = requests.post(ASSEMBLY_UPLOAD_URL, headers=headers, data=f)
    upload_res.raise_for_status()
    audio_url = upload_res.json()["upload_url"]

    # Request transcription
    transcript_req = {"audio_url": audio_url}
    trans_res = requests.post(ASSEMBLY_TRANSCRIBE_URL, headers=headers, json=transcript_req)
    trans_res.raise_for_status()
    transcript_id = trans_res.json()["id"]

    # Poll until transcription is done
    while True:
        poll_res = requests.get(f"{ASSEMBLY_TRANSCRIBE_URL}/{transcript_id}", headers=headers)
        poll_res.raise_for_status()
        status = poll_res.json()["status"]
        if status == "completed":
            text = poll_res.json()["text"]
            break
        elif status == "error":
            raise HTTPException(status_code=500, detail="Transcription failed")

    # Send transcription to Murf for TTS
    murf_headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    murf_payload = {
        "voice_id": "en-IN-aarav",
        "text": text,
        "output_format": "mp3",
        "style": "Conversational"
    }
    murf_res = requests.post(MURF_API_URL, json=murf_payload, headers=murf_headers)
    murf_res.raise_for_status()
    murf_data = murf_res.json()
    murf_audio_url = murf_data.get("audioFile")

    if not murf_audio_url:
        raise HTTPException(status_code=500, detail="Murf audio generation failed")

    return {"audio_url": murf_audio_url, "transcription": text}
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )