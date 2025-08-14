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

---

## 🏗 System Architecture

### Diagram
![EchoCraft Architecture](assets/echocraft_architecture.png)

---

### Components

1. **User Interface (UI)**  
   - Accepts text or voice input.  
   - Displays conversation history.  
   - Plays generated audio output.  

2. **Voice Input Handling**  
   - Captures microphone audio.  
   - Sends to AssemblyAI for transcription.

3. **Text Input Handling**  
   - Directly sends typed messages to Gemini API.

4. **AssemblyAI API (Speech-to-Text)**  
   - Converts voice input to text.  

5. **Gemini API (LLM)**  
   - Generates intelligent responses based on input and session memory.

6. **Murf API (Text-to-Speech)**  
   - Converts Gemini's text output into natural-sounding speech.

7. **Session Management**  
   - Maintains conversation context for each `session_id`.

---

### Working Flow

**Voice Input Path**  
1. User speaks → Audio recorded.  
2. Audio → AssemblyAI API → Transcribed text.  
3. Text → Gemini API → Response text.  
4. Response → Murf API → Audio output.  
5. Audio plays in UI.

**Text Input Path**  
1. User types message.  
2. Text → Gemini API → Response text.  
3. Response → Murf API → Audio output.  
4. Audio plays in UI.

**Memory Management**  
- Session IDs store past conversation context.  
- Sent with each request to Gemini API for coherent replies.

---