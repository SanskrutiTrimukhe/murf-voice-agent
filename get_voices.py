import requests
import os
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
print("Loaded API Key:", MURF_API_KEY)

headers = {
    "accept": "application/json",
    "api-key": MURF_API_KEY
}

response = requests.get("https://api.murf.ai/v1/speech/voices", headers=headers)

if response.status_code == 200:
    voices = response.json()
    print("\nAvailable Voices:\n")
    for voice in voices:
        print(f"{voice['voiceId']} - {voice['displayName']} ({voice['accent']}, {voice['gender']})")
else:
    print("Error:", response.text)
