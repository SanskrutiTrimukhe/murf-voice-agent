from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from fastapi import File, UploadFile
from fastapi.responses import JSONResponse
import shutil

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can change this to specific domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder (CSS, JS, images)
app.mount("/static", StaticFiles(directory="day-1/static"), name="static")

# Setup Jinja2 for HTML templating
templates = Jinja2Templates(directory="day-1/templates")

# Environment variables
MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

# Data model
class InputText(BaseModel):
    text: str

# Serve the frontend HTML page
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Generate audio using Murf API
@app.post("/generate-audio/")
async def generate_audio(input_text: InputText):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="MURF_API_KEY not found")

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "voice_id": "en-IN-aarav",  # You can change this to any valid Murf voice
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