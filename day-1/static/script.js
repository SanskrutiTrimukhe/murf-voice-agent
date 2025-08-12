document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Element References (Unchanged) ---
    const switchToSpeakBtn = document.getElementById("switchToSpeakBtn");
    const switchToTypeBtn = document.getElementById("switchToTypeBtn");
    const speakModeContainer = document.getElementById("speakModeContainer");
    const typeModeContainer = document.getElementById("typeModeContainer");
    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const textQueryInput = document.getElementById("textQueryInput");
    const submitTextBtn = document.getElementById("submitTextQuery");
    const statusText = document.getElementById("statusText");
    const resultsContainer = document.getElementById("resultsContainer");
    const transcriptionText = document.getElementById("transcriptionText");
    const responseText = document.getElementById("responseText");
    
    // --- State Variables (Unchanged) ---
    const audioPlayer = new Audio();
    let mediaRecorder;
    let audioChunks = [];
    let sessionId = null;

    // --- Session Management (Unchanged) ---
    const initializeSession = () => {
        // ... (function remains the same)
        const params = new URLSearchParams(window.location.search);
        let currentSessionId = params.get('session_id');

        if (!currentSessionId) {
            currentSessionId = Date.now().toString(36) + Math.random().toString(36).substring(2);
            window.history.replaceState({}, '', `${window.location.pathname}?session_id=${currentSessionId}`);
        }
        
        sessionId = currentSessionId;
        console.log("Session ID Initialized:", sessionId);
    };

    // --- Voice Input Logic (Unchanged) ---
    async function startRecording() {
        // ... (function remains the same)
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            audioChunks = [];
            mediaRecorder.ondataavailable = (event) => { audioChunks.push(event.data); };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendAudioToServer(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.textContent = "Listening... 🎙️";

        } catch (error) {
            // NEW: More specific error handling for microphone access
            console.error("Error accessing microphone:", error);
            statusText.textContent = "Could not access microphone. Please grant permission in your browser settings.";
            playClientSideFallbackAudio("I can't access your microphone. Please grant permission and try again.");
            startBtn.disabled = false;
        }
    }
    
    function stopRecording() {
        // ... (function remains the same)
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
    }

    // --- NEW: Centralized API Call and Error Handling Logic ---
    async function sendRequest(endpoint, options) {
        // Reset UI for a new request
        resultsContainer.classList.add('hidden');
        startBtn.disabled = true;
        stopBtn.disabled = true;
        submitTextBtn.disabled = true;
        statusText.textContent = "Connecting to the agent...";

        try {
            const response = await fetch(endpoint, options);
            const data = await response.json();

            if (!response.ok) {
                // Server returned an error (e.g., 500), but we got a JSON response
                console.error("API Error Response:", data);
                handleApiError(data);
                return;
            }

            // --- Success Case ---
            console.log("API Success Response:", data);
            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You said: "${data.transcription}"`;
            responseText.textContent = `Agent says: "${data.llm_response}"`;
            
            const onFinishedPlaying = () => {
                setInputMode('speak'); // Default back to speak mode
                statusText.textContent = "Ready. Press 'Start Recording' to speak again.";
            };
            playAudioSequentially(data.audio_urls, onFinishedPlaying);

        } catch (error) {
            // Network error or server is down - we won't have a JSON response
            console.error("Network or Fetch Error:", error);
            handleApiError({ detail: "Cannot connect to the server. Please check your connection." });
        }
    }

    // --- NEW: Function to handle errors from the API ---
    function handleApiError(errorData) {
        statusText.textContent = `Error: ${errorData.detail || "An unknown error occurred."}`;

        // If the server sent a fallback audio, play it.
        if (errorData.fallback_audio_url) {
            playAudioSequentially([errorData.fallback_audio_url], () => setInputMode('speak'));
        } else {
            // Otherwise, use the browser's voice as a last resort.
            playClientSideFallbackAudio("I'm having trouble connecting right now. Please try again later.");
            setInputMode('speak');
        }

        // If the error response contains the LLM text (e.g., TTS failed), display it
        if (errorData.llm_response) {
            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You said: "${errorData.transcription}"`;
            responseText.textContent = `Agent (text only): "${errorData.llm_response}"`;
        }
    }

    // --- NEW: Client-side only fallback audio generator ---
    function playClientSideFallbackAudio(message) {
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(message);
            window.speechSynthesis.speak(utterance);
        } else {
            console.warn("Browser TTS not available for fallback audio.");
        }
    }

    // --- Refactored Functions to use the central handler ---
    function sendAudioToServer(audioBlob) {
        statusText.textContent = "Processing your audio...";
        const formData = new FormData();
        formData.append("file", audioBlob, "user_audio.webm");
        sendRequest(`/agent/chat/${sessionId}`, { method: "POST", body: formData });
    }

    function sendTextToServer(text) {
        statusText.textContent = "Sending your message...";
        sendRequest(`/agent/chat/text/${sessionId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
    }

    // --- Audio Player and UI Switching (Mostly Unchanged) ---
    function playAudioSequentially(urls, onFinished) {
        // ... (function remains the same, but now used for fallbacks too)
        let index = 0;
        if (!urls || urls.length === 0) {
            if (onFinished) onFinished();
            return;
        }
        
        audioPlayer.src = urls[index];
        statusText.textContent = "Agent is speaking... 🔊";
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

    function setInputMode(mode) {
        // ... (function remains the same, but enables buttons at the end)
        const isSpeakMode = mode === 'speak';
        speakModeContainer.classList.toggle('hidden', !isSpeakMode);
        typeModeContainer.classList.toggle('hidden', isSpeakMode);
        // Reset buttons to be ready
        startBtn.disabled = false;
        stopBtn.disabled = true;
        submitTextBtn.disabled = false;
        textQueryInput.value = "";
        statusText.textContent = isSpeakMode ? "Press 'Start Recording' to begin." : "Type your message and press send.";
    }

    // --- Event Listeners (Refactored to call new functions) ---
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    submitTextBtn.addEventListener("click", () => {
        const query = textQueryInput.value.trim();
        if (query) sendTextToServer(query);
    });
    switchToSpeakBtn.addEventListener("click", () => setInputMode('speak'));
    switchToTypeBtn.addEventListener("click", () => setInputMode('type'));
    
    // --- Initialization ---
    initializeSession();
    setInputMode('speak');
});
