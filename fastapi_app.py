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
import json # Import json for debugging

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

# --- In-memory datastore for chat histories ---
# Format: { "session_id": [{"role": "user", "parts": [...]}, {"role": "model", "parts": [...]}] }
chat_histories = {}

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
class TextChatRequest(BaseModel):
    text: str

# --- Helper Function to Split Text for Murf ---
def split_text_into_chunks(text: str, chunk_size: int = 2900):
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    # Simplified splitting logic for robustness
    while len(text) > 0:
        chunk = text[:chunk_size]
        last_punctuation = -1
        if len(text) > chunk_size:
            for p in ['.', '!', '?']:
                pos = chunk.rfind(p)
                if pos > last_punctuation:
                    last_punctuation = pos
            if last_punctuation != -1:
                chunk = chunk[:last_punctuation + 1]
        
        chunks.append(chunk.strip())
        text = text[len(chunk):].strip()
    return chunks

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Conversational Voice Endpoint ---
@app.post("/agent/chat/{session_id}")
async def agent_voice_chat(session_id: str, file: UploadFile = File(...)):
    print(f"\n--- Handling VOICE request for session_id: {session_id} ---")

    # STT Pipeline
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
        if os.path.exists(temp_path): os.remove(temp_path)

    transcript_request = {"audio_url": audio_url_assembly}
    transcript_response = requests.post(ASSEMBLY_TRANSCRIBE_URL, json=transcript_request, headers=headers_assembly)
    transcript_id = transcript_response.json()["id"]

    while True:
        polling_response = requests.get(f"{ASSEMBLY_TRANSCRIBE_URL}/{transcript_id}", headers=headers_assembly)
        transcription_result = polling_response.json()
        if transcription_result["status"] == "completed":
            user_text = transcription_result.get("text")
            break
        elif transcription_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Transcription failed: {transcription_result['error']}")
        time.sleep(2)

    if not user_text:
        return JSONResponse(content={"audio_urls": ["https://murf-public.s3.amazonaws.com/temp/audio-files/f39c8c9a-1f19-4279-b14e-f982e583765b.mp3"], "transcription": ""})

    # History, LLM, and TTS logic is shared
    return await handle_chat_logic(session_id, user_text)

# --- Conversational Text Endpoint ---
@app.post("/agent/chat/text/{session_id}")
async def agent_text_chat(session_id: str, request_body: TextChatRequest):
    print(f"\n--- Handling TEXT request for session_id: {session_id} ---")
    user_text = request_body.text
    if not user_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    # History, LLM, and TTS logic is shared
    return await handle_chat_logic(session_id, user_text)

# --- Shared Chat Logic Function ---
async def handle_chat_logic(session_id: str, user_text: str):
    # 1. Get history and append user message
    history = chat_histories.get(session_id, []).copy()
    history.append({"role": "user", "parts": [{"text": user_text}]})
    print(f"[DEBUG] History for LLM: {history}")

    # 2. Construct payload for Gemini
    payload_gemini = {
        "contents": history,
        "system_instruction": {
            "parts": [{"text": "Keep your response concise, helpful, and to the point. Be conversational."}]
        }
    }
    
    # 3. Call Gemini API
    try:
        headers_gemini = {"Content-Type": "application/json"}
        response_gemini = requests.post(GEMINI_API_URL, headers=headers_gemini, json=payload_gemini)
        response_gemini.raise_for_status()
        data = response_gemini.json()
        if "candidates" not in data or not data["candidates"]:
            raise HTTPException(status_code=500, detail=f"Gemini API returned no candidates. Response: {data}")
        llm_response_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API request failed: {str(e)}")

    # 4. Append model response and save history
    history.append({"role": "model", "parts": [{"text": llm_response_text}]})
    chat_histories[session_id] = history
    print(f"[DEBUG] Saved history for session '{session_id}'.")

    # 5. TTS Pipeline
    text_chunks = split_text_into_chunks(llm_response_text)
    audio_urls = []
    headers_murf = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    for chunk in text_chunks:
        payload_murf = {"voice_id": "en-IN-aarav", "text": chunk, "style": "Conversational"}
        try:
            response_murf = requests.post(MURF_API_URL, json=payload_murf, headers=headers_murf)
            response_murf.raise_for_status()
            if audio_url := response_murf.json().get("audioFile"):
                audio_urls.append(audio_url)
        except requests.RequestException as e:
            print(f"Murf API failed for a chunk: {str(e)}")
            continue
    
    if not audio_urls:
        raise HTTPException(status_code=500, detail="Murf audio generation failed.")

    # 6. Return response
    return {"audio_urls": audio_urls, "transcription": user_text, "llm_response": llm_response_text}
