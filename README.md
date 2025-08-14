# 🎙️ EchoCraft – AI Voice Agent with Murf API

EchoCraft is an AI-powered voice assistant that converts text to realistic speech, records your voice, and echoes it back. Built with **FastAPI**, **JavaScript**, and **Murf API**, this project demonstrates how to make interactive, memory-aware voice agents.

---

## 🚀 Features
- **Text-to-Speech (TTS)** using Murf API for lifelike voices.
- **Echo Bot** – record your voice and play it back.
- **Conversation Memory** via session IDs.
- **Clean UI** with background, title, and clear audio flow.
- **API-based Backend** for easy integration.

---

## 🛠️ Tech Stack
**Frontend:** HTML, CSS, JavaScript (`static/`, `templates/`)  
**Backend:** FastAPI (`app.py`, `fastapi_app.py`)  
**AI/TTS Engine:** Murf API (`get_voices.py`)  
**Other Tools:** dotenv, requests, CORS Middleware

---

## 📂 Project Structure
```plaintext
MURF-VOICE-AGENT/
│-- app.py                 # Main FastAPI server
│-- fastapi_app.py         # API handling logic
│-- get_voices.py          # Murf API integration
│-- .env                   # Environment variables (Murf API key)
│-- uploads/               # Recorded audio storage
│-- static/                # JS, CSS, images
│-- templates/             # HTML templates
│-- README.md               # Project documentation
