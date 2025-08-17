from fastapi import FastAPI, Request, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect
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

# --- Fallback Audio URL ---
FALLBACK_AUDIO_URL = "https://murf-public.s3.amazonaws.com/temp/audio-files/f39c8c9a-1f19-4279-b14e-f982e583765b.mp3"

# --- Helper Function (Unchanged) ---
def split_text_into_chunks(text: str, chunk_size: int = 2900):
    return [text]

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- MODIFIED: WebSocket Endpoint for Streaming Audio ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected to WebSocket for audio streaming.")
    
    # Generate a unique filename for each recording session
    output_filename = f"uploads/streamed_audio_{uuid.uuid4()}.webm"
    
    try:
        # Open the file in write-binary mode
        with open(output_filename, "wb") as audio_file:
            # Loop indefinitely to receive audio chunks
            while True:
                # Receive audio data as bytes from the client
                data = await websocket.receive_bytes()
                # Write the received bytes to the file
                audio_file.write(data)
                
    except WebSocketDisconnect:
        print(f"Client disconnected. Audio stream saved to {output_filename}")
    except Exception as e:
        print(f"An error occurred during streaming: {e}")
        # Clean up the partially created file if an error occurs
        if os.path.exists(output_filename):
            os.remove(output_filename)
        print("Cleaned up partially saved audio file.")

# --- The rest of your HTTP endpoints remain the same ---
@app.post("/agent/chat/{session_id}")
async def agent_voice_chat(session_id: str, file: UploadFile = File(...)):
    # ... (existing code)
    pass

@app.post("/agent/chat/text/{session_id}")
async def agent_text_chat(session_id: str, request_body: BaseModel):
    # ... (existing code)
    pass

async def handle_chat_logic(session_id: str, user_text: str):
    # ... (existing code)
    pass
