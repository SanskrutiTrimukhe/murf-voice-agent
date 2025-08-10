document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Element References ---
    const switchToSpeakBtn = document.getElementById("switchToSpeakBtn");
    const switchToTypeBtn = document.getElementById("switchToTypeBtn");
    const speakModeContainer = document.getElementById("speakModeContainer");
    const typeModeContainer = document.getElementById("typeModeContainer");
    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const textQueryInput = document.getElementById("textQueryInput");
    const submitTextBtn = document.getElementById("submitTextQuery");
    const statusText = document.getElementById("statusText");
    
    // NEW: Get the container for the results
    const resultsContainer = document.getElementById("resultsContainer");
    const transcriptionText = document.getElementById("transcriptionText");
    const responseText = document.getElementById("responseText");
    
    const audioPlayer = new Audio();
    let mediaRecorder;
    let audioChunks = [];

    // --- Helper function to reset the UI ---
    function resetUI() {
        resultsContainer.classList.add('hidden'); // Hide results
        transcriptionText.textContent = "";
        responseText.textContent = "";
    }

    // --- Mode Switching Logic ---
    function setInputMode(mode) {
        const isSpeakMode = mode === 'speak';
        speakModeContainer.classList.toggle('hidden', !isSpeakMode);
        typeModeContainer.classList.toggle('hidden', isSpeakMode);
        switchToSpeakBtn.classList.toggle('active', isSpeakMode);
        switchToTypeBtn.classList.toggle('active', !isSpeakMode);
        statusText.textContent = isSpeakMode ? "Press 'Start Recording' to begin." : "Type your message and press send.";
        resetUI();
    }

    switchToSpeakBtn.addEventListener("click", () => setInputMode('speak'));
    switchToTypeBtn.addEventListener("click", () => setInputMode('type'));
    
    // --- Voice Input Logic ---
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
                mediaRecorder.onstop = () => {
                    sendAudioToLlm(new Blob(audioChunks, { type: 'audio/wav' }));
                    audioChunks = [];
                };
                startBtn.addEventListener("click", () => {
                    mediaRecorder.start();
                    statusText.textContent = "Listening... 🎙️";
                    resetUI();
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                });
                stopBtn.addEventListener("click", () => {
                    mediaRecorder.stop();
                    statusText.textContent = "Thinking...";
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                });
            })
            .catch(err => {
                speakModeContainer.innerHTML = "<p class='status-area'>Microphone access denied. Please enable it to use speak mode.</p>";
                setInputMode('type');
            });
    }

    async function sendAudioToLlm(audioBlob) {
        const formData = new FormData();
        formData.append("file", audioBlob, "user_audio.wav");
        statusText.textContent = "Transcribing and thinking...";
        try {
            const response = await fetch("/llm/query", { method: "POST", body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Failed to process audio.");
            
            // Show results
            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You said: "${data.transcription}"`;
            responseText.textContent = data.llm_response;
            
            playAudioSequentially(data.audio_urls, () => setInputMode('speak'));
        } catch (error) {
            statusText.textContent = `Error: ${error.message}`;
        }
    }

    // --- Text Input Logic ---
    submitTextBtn.addEventListener("click", () => {
        const query = textQueryInput.value.trim();
        if (query) {
            resetUI();
            sendTextToLlm(query);
        }
    });

    async function sendTextToLlm(text) {
        statusText.textContent = "Thinking...";
        submitTextBtn.disabled = true;
        textQueryInput.value = "";
        
        try {
            const response = await fetch("/llm/text_query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Failed to process text.");

            // Show results
            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You wrote: "${text}"`;
            responseText.textContent = data.llm_response;
            
            playAudioSequentially(data.audio_urls, () => {
                setInputMode('type');
                submitTextBtn.disabled = false;
            });
        } catch (error) {
            statusText.textContent = `Error: ${error.message}`;
            submitTextBtn.disabled = false;
        }
    }

    // --- Shared Audio Player ---
    function playAudioSequentially(urls, onFinished) {
        let index = 0;
        if (!urls || urls.length === 0) {
            if (onFinished) onFinished();
            return;
        }
        audioPlayer.src = urls[index];
        statusText.textContent = "Playing response... 🔊";
        audioPlayer.play();
        audioPlayer.onended = () => {
            index++;
            if (index < urls.length) {
                audioPlayer.src = urls[index];
                audioPlayer.play();
            } else {
                if (onFinished) onFinished();
            }
        };
        audioPlayer.onerror = () => {
            statusText.textContent = "Error playing audio.";
            if (onFinished) onFinished();
        };
    }
    
    // Set initial state on page load
    setInputMode('speak');
});
  