from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_API_URL = "https://api.murf.ai/v1/speech/generate"

class InputText(BaseModel):
    text: str

@app.post("/generate-audio/")
def generate_audio(input_text: InputText):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="MURF_API_KEY not found")

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "voice_id": "en-UK-hazel",
        "text": input_text.text.strip(),
        "output_format": "mp3",
        "style": "Conversational"
    }

    print("DEBUG Payload:", payload)

    response = requests.post(MURF_API_URL, json=payload, headers=headers)

    print("DEBUG STATUS:", response.status_code)
    print("DEBUG RESPONSE:", response.text)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()
    audio_url = data.get("audioFile")

    if not audio_url:
        raise HTTPException(status_code=400, detail="No audio URL returned")

    return {"audio_url": audio_url}

