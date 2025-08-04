async function generateAudio() {
  const input = document.getElementById("textInput").value;
  const status = document.getElementById("statusText");
  status.textContent = 'Generating audio…';

  try {
    const resp = await fetch("http://localhost:8000/generate-audio/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input })
    });

    const data = await resp.json();
    if (resp.ok && data.audio_url) {
      const audio = document.getElementById("audioPlayer");
      audio.src = data.audio_url;
      await audio.play();
      status.textContent = 'Playing audio!';
    } else {
      status.textContent = 'Error: ' + (data.detail || 'Failed to generate');
    }
  } catch (err) {
    status.textContent = 'Network or server error';
  }
}
