from fastapi import FastAPI, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
import shutil
import uuid
import time
import re

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

# --- Environment Variables ---
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLY_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- API URLs ---
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"
ASSEMBLY_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLY_TRANSCRIBE_URL = "https://api.assemblyai.com/v2/transcript"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# --- Upload Directory ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Pydantic Models ---
class InputText(BaseModel):
    text: str

# --- Helper Function to Split Text for Murf ---
def split_text_into_chunks(text: str, chunk_size: int = 2900):
    """
    Splits text into chunks of a specified size, respecting sentence boundaries.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    while len(text) > chunk_size:
        # Find the last sentence-ending punctuation before the chunk limit
        split_pos = -1
        for char in ['.', '!', '?']:
            pos = text.rfind(char, 0, chunk_size)
            if pos > split_pos:
                split_pos = pos
        
        # If no sentence end found, force a split at the nearest space
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, chunk_size)
        
        # If no space found, force split at chunk_size
        if split_pos == -1:
            split_pos = chunk_size
        
        chunk = text[:split_pos + 1]
        chunks.append(chunk.strip())
        text = text[split_pos + 1:].strip()
    
    if text:
        chunks.append(text)
        
    return chunks

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- DAY 9: Full Non-Streaming Pipeline ---
@app.post("/llm/query")
async def llm_voice_query(file: UploadFile = File(...)):
   
    if not ASSEMBLY_API_KEY or not GEMINI_API_KEY or not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="One or more API keys are missing.")

    # 1. Save and Upload Audio to AssemblyAI
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        headers_assembly = {"authorization": ASSEMBLY_API_KEY}
        with open(temp_path, "rb") as f:
            upload_response = requests.post(ASSEMBLY_UPLOAD_URL, headers=headers_assembly, data=f)
        upload_response.raise_for_status()
        audio_url_assembly = upload_response.json()["upload_url"]

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # 2. Transcribe Audio with AssemblyAI
    transcript_request = {"audio_url": audio_url_assembly}
    transcript_response = requests.post(ASSEMBLY_TRANSCRIBE_URL, json=transcript_request, headers=headers_assembly)
    transcript_response.raise_for_status()
    transcript_id = transcript_response.json()["id"]

    # Poll for transcription result
    while True:
        polling_response = requests.get(f"{ASSEMBLY_TRANSCRIBE_URL}/{transcript_id}", headers=headers_assembly)
        polling_response.raise_for_status()
        transcription_result = polling_response.json()
        if transcription_result["status"] == "completed":
            user_text = transcription_result["text"]
            break
        elif transcription_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Transcription failed: {transcription_result['error']}")
        time.sleep(2)

    if not user_text:
        # Handle cases where transcription is empty
        return JSONResponse(content={"audio_url": "https://murf-public.s3.amazonaws.com/temp/61e0b5e0-5a39-4d7a-8b8f-3b3a3b3a3b3a.mp3", "transcription": ""}) # Provide a default silent or "I heard nothing" audio

    # 3. Send Transcribed Text to Gemini LLM
    headers_gemini = {"Content-Type": "application/json"}
    payload_gemini = {"contents": [{"parts": [{"text": "Keep your response concise and to the point. " + user_text}]}]}
    
    try:
        response_gemini = requests.post(GEMINI_API_URL, headers=headers_gemini, json=payload_gemini)
        response_gemini.raise_for_status()
        data = response_gemini.json()
        llm_response_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (requests.RequestException, KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail=f"Gemini API request failed: {str(e)}")

    # 4. Split LLM Response for Murf
    text_chunks = split_text_into_chunks(llm_response_text)

    # 5. Generate Audio with Murf for each chunk
    audio_urls = []
    headers_murf = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    
    for chunk in text_chunks:
        payload_murf = {
            "voice_id": "en-IN-aarav",
            "text": chunk,
            "output_format": "mp3",
            "style": "Conversational"
        }
        try:
            response_murf = requests.post(MURF_API_URL, json=payload_murf, headers=headers_murf)
            response_murf.raise_for_status()
            murf_data = response_murf.json()
            if audio_url := murf_data.get("audioFile"):
                audio_urls.append(audio_url)
        except requests.RequestException as e:
            # Continue to next chunk if one fails, or handle error as needed
            print(f"Murf API failed for a chunk: {str(e)}")
            continue

    if not audio_urls:
        raise HTTPException(status_code=500, detail="Murf audio generation failed for all text chunks.")

    # 6. Return the list of audio URLs
    # The client will be responsible for playing these sequentially.
    return {"audio_urls": audio_urls, "transcription": user_text, "llm_response": llm_response_text}

# Add this new endpoint to your fastapi_app.py

class InputText(BaseModel):
    text: str

@app.post("/llm/text_query")
async def llm_text_query(input_text: InputText):
    
    if not GEMINI_API_KEY or not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY or MURF_API_KEY is missing.")

    user_text = input_text.text

    # 1. Send Text to Gemini LLM
    headers_gemini = {"Content-Type": "application/json"}
    prompt = f"Please provide a helpful and friendly response to the following user query: \"{user_text}\""
    payload_gemini = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response_gemini = requests.post(GEMINI_API_URL, headers=headers_gemini, json=payload_gemini)
        response_gemini.raise_for_status()
        data = response_gemini.json()
        llm_response_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (requests.RequestException, KeyError, IndexError) as e:
        raise HTTPException(status_code=500, detail=f"Gemini API request failed: {str(e)}")

    # 2. Split LLM Response for Murf (if needed)
    text_chunks = split_text_into_chunks(llm_response_text)

    # 3. Generate Audio with Murf
    audio_urls = []
    headers_murf = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    
    for chunk in text_chunks:
        payload_murf = {
            "voice_id": "en-IN-aarav",
            "text": chunk,
            "style": "Conversational"
        }
        try:
            response_murf = requests.post(MURF_API_URL, json=payload_murf, headers=headers_murf)
            response_murf.raise_for_status()
            murf_data = response_murf.json()
            if audio_url := murf_data.get("audioFile"):
                audio_urls.append(audio_url)
        except requests.RequestException:
            continue

    if not audio_urls:
        raise HTTPException(status_code=500, detail="Murf audio generation failed.")

    # 4. Return Audio URLs and the LLM's text response
    return {"audio_urls": audio_urls, "llm_response": llm_response_text}

# --- Global Exception Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )

