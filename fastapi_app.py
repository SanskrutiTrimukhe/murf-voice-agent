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

# Mount static folder and templates
app.mount("/static", StaticFiles(directory="day-1/static"), name="static")
templates = Jinja2Templates(directory="day-1/templates")

# --- In-memory datastore for chat histories ---
chat_histories = {}

# --- Environment Variables & API Keys ---
# To simulate errors, set the respective key to None or an empty string
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

# --- NEW: Fallback Audio URL ---
# A pre-generated audio file for generic error messages
FALLBACK_AUDIO_URL = "https://murf-public.s3.amazonaws.com/temp/audio-files/f39c8c9a-1f19-4279-b14e-f982e583765b.mp3" # "I'm having trouble connecting right now"

# --- Helper Function (Unchanged) ---
def split_text_into_chunks(text: str, chunk_size: int = 2900):
    # ... (function remains the same)
    return [text] # Simplified for example

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Conversational Voice Endpoint with Error Handling ---
@app.post("/agent/chat/{session_id}")
async def agent_voice_chat(session_id: str, file: UploadFile = File(...)):
    print(f"\n--- Handling VOICE request for session_id: {session_id} ---")

    # --- NEW: STT Pipeline with Error Handling ---
    user_text = None
    try:
        # Simulate API Key error for STT
        if not ASSEMBLY_API_KEY:
            raise ValueError("AssemblyAI API key is not configured.")

        # Save temporary file
        temp_filename = f"{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload to AssemblyAI
        headers_assembly = {"authorization": ASSEMBLY_API_KEY}
        with open(temp_path, "rb") as f:
            upload_response = requests.post(ASSEMBLY_UPLOAD_URL, headers=headers_assembly, data=f)
        upload_response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        audio_url_assembly = upload_response.json()["upload_url"]

        # Request transcription
        transcript_request = {"audio_url": audio_url_assembly}
        transcript_response = requests.post(ASSEMBLY_TRANSCRIBE_URL, json=transcript_request, headers=headers_assembly)
        transcript_response.raise_for_status()
        transcript_id = transcript_response.json()["id"]

        # Poll for result
        while True:
            polling_response = requests.get(f"{ASSEMBLY_TRANSCRIBE_URL}/{transcript_id}", headers=headers_assembly)
            polling_response.raise_for_status()
            transcription_result = polling_response.json()
            if transcription_result["status"] == "completed":
                user_text = transcription_result.get("text")
                print(f"Transcription successful: '{user_text}'")
                break
            elif transcription_result["status"] == "error":
                raise Exception(f"Transcription failed: {transcription_result['error']}")
            time.sleep(2)

    except (requests.RequestException, ValueError, Exception) as e:
        error_message = f"Failed during Speech-to-Text process: {e}"
        print(f"[ERROR] {error_message}")
        # Return a structured error with fallback audio
        return JSONResponse(
            status_code=500,
            content={"detail": "I'm having trouble understanding you right now. Please try again.", "fallback_audio_url": FALLBACK_AUDIO_URL}
        )
    finally:
        # Clean up the temporary file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

    if not user_text:
        return JSONResponse(
            status_code=400,
            content={"detail": "I couldn't detect any speech in the audio. Please speak clearly.", "fallback_audio_url": FALLBACK_AUDIO_URL}
        )

    # All good, proceed to shared logic
    return await handle_chat_logic(session_id, user_text)


# --- Conversational Text Endpoint (Unchanged) ---
@app.post("/agent/chat/text/{session_id}")
async def agent_text_chat(session_id: str, request_body: BaseModel):
    user_text = request_body.text
    return await handle_chat_logic(session_id, user_text)

# --- Shared Chat Logic with Error Handling ---
async def handle_chat_logic(session_id: str, user_text: str):
    history = chat_histories.get(session_id, []).copy()
    history.append({"role": "user", "parts": [{"text": user_text}]})

    # --- NEW: LLM (Gemini) Call with Error Handling ---
    try:
        if not GEMINI_API_KEY or "YOUR_API_KEY" in GEMINI_API_URL:
            raise ValueError("Gemini API key is not configured.")
        
        payload_gemini = {"contents": history}
        headers_gemini = {"Content-Type": "application/json"}
        response_gemini = requests.post(GEMINI_API_URL, headers=headers_gemini, json=payload_gemini, timeout=30)
        response_gemini.raise_for_status()
        data = response_gemini.json()
        
        if "candidates" not in data or not data["candidates"]:
            raise Exception(f"Gemini API returned no candidates. Response: {data}")
            
        llm_response_text = data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"LLM Response: '{llm_response_text}'")

    except (requests.RequestException, ValueError, Exception) as e:
        error_message = f"Failed during LLM API call: {e}"
        print(f"[ERROR] {error_message}")
        return JSONResponse(
            status_code=500,
            content={"detail": "I'm having trouble thinking of a response right now. Please try again later.", "fallback_audio_url": FALLBACK_AUDIO_URL}
        )

    history.append({"role": "model", "parts": [{"text": llm_response_text}]})
    chat_histories[session_id] = history

    # --- NEW: TTS (Murf) Pipeline with Error Handling ---
    audio_urls = []
    try:
        if not MURF_API_KEY:
            raise ValueError("Murf.ai API key is not configured.")

        text_chunks = split_text_into_chunks(llm_response_text)
        headers_murf = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        
        for chunk in text_chunks:
            payload_murf = {"voice_id": "en-IN-aarav", "text": chunk, "style": "Conversational"}
            response_murf = requests.post(MURF_API_URL, json=payload_murf, headers=headers_murf, timeout=20)
            response_murf.raise_for_status()
            if audio_url := response_murf.json().get("audioFile"):
                audio_urls.append(audio_url)
            else:
                raise Exception("Murf API did not return an audio file for a chunk.")

    except (requests.RequestException, ValueError, Exception) as e:
        error_message = f"Failed during Text-to-Speech process: {e}"
        print(f"[ERROR] {error_message}")
        # IMPORTANT: Even if TTS fails, we can still return the text response and a fallback audio
        return JSONResponse(
            status_code=500,
            content={
                "detail": "I've generated a response, but I'm having trouble speaking it.",
                "fallback_audio_url": FALLBACK_AUDIO_URL,
                "transcription": user_text,
                "llm_response": llm_response_text # Send the text so the user can at least read it
            }
        )

    return {"audio_urls": audio_urls, "transcription": user_text, "llm_response": llm_response_text}
