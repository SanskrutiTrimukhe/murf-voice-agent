// TEXT TO SPEECH LOGIC
async function generateAudio() {
  const input = document.getElementById("textInput").value.trim();
  const status = document.getElementById("statusText");
  const audio = document.getElementById("audioPlayer");

  if (!input) {
    status.textContent = "Please enter something for me to convert!";
    return;
  }

  status.textContent = "Generating voice... hang tight.";
  audio.style.display = "none";

  try {
    const response = await fetch("http://localhost:8000/generate-audio/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input })
    });

    const data = await response.json();

    if (response.ok && data.audio_url) {
      audio.src = data.audio_url;
      audio.load();
      audio.style.display = "block";
      status.textContent = "Voice is ready! Press play to listen. 🎧";
    } else {
      status.textContent = "Error: " + (data.detail || "Failed to generate voice.");
    }
  } catch (err) {
    status.textContent = "Something went wrong. Please try again.";
  }
}

// ECHO BOT v2
let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startRecording");
const stopBtn = document.getElementById("stopRecording");
const echoStatus = document.getElementById("echoStatus");
const echoAudio = document.getElementById("echoAudio");

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        echoStatus.textContent = "Uploading your recording to Echo Bot v2...";

        // Send to /tts/echo
        const formData = new FormData();
        formData.append("file", audioBlob, "echo.wav");

        fetch("http://localhost:8000/tts/echo", {
          method: "POST",
          body: formData
        })
          .then(response => response.json())
          .then(data => {
            if (data.audio_url) {
              echoAudio.src = data.audio_url;
              echoAudio.style.display = "block";
              echoStatus.textContent = `Murf says: "${data.transcription}" 🎤`;
            } else {
              echoStatus.textContent = "Failed to get Murf audio.";
            }
          })
          .catch(error => {
            echoStatus.textContent = "❌ Echo failed.";
            console.error("Error:", error);
          });

        audioChunks = [];
      };

      startBtn.addEventListener("click", () => {
        mediaRecorder.start();
        echoStatus.textContent = "Recording... 🎙️";
        startBtn.disabled = true;
        stopBtn.disabled = false;
      });

      stopBtn.addEventListener("click", () => {
        mediaRecorder.stop();
        echoStatus.textContent = "Processing your voice...";
        startBtn.disabled = false;
        stopBtn.disabled = true;
      });
    })
    .catch(err => {
      console.error("Microphone access denied:", err);
      echoStatus.textContent = "Microphone access denied. Please allow access.";
    });
} else {
  echoStatus.textContent = "Your browser doesn't support audio recording.";
}
