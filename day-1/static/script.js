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
    const resultsContainer = document.getElementById("resultsContainer");
    const transcriptionText = document.getElementById("transcriptionText");
    const responseText = document.getElementById("responseText");
    
    // --- State Variables ---
    const audioPlayer = new Audio();
    let mediaRecorder;
    let audioChunks = [];
    let sessionId = null;

    // --- Session Management ---
    const initializeSession = () => {
        const params = new URLSearchParams(window.location.search);
        let currentSessionId = params.get('session_id');

        if (!currentSessionId) {
            currentSessionId = Date.now().toString(36) + Math.random().toString(36).substring(2);
            window.history.replaceState({}, '', `${window.location.pathname}?session_id=${currentSessionId}`);
        }
        
        sessionId = currentSessionId;
        console.log("Session ID Initialized:", sessionId);
    };

    // --- Voice Input Logic ---
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            audioChunks = [];
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendAudioToLlm(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.textContent = "Listening... 🎙️";

        } catch (error) {
            console.error("Error accessing microphone:", error);
            statusText.textContent = "Could not access microphone. Please grant permission.";
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            statusText.textContent = "Processing your audio...";
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    async function sendAudioToLlm(audioBlob) {
        const formData = new FormData();
        formData.append("file", audioBlob, "user_audio.webm");
        statusText.textContent = "Transcribing and thinking...";
        
        try {
            const response = await fetch(`/agent/chat/${sessionId}`, { method: "POST", body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to process audio.");
            }
            const data = await response.json();
            
            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You said: "${data.transcription}"`;
            responseText.textContent = `Agent says: "${data.llm_response}"`;
            
            const onFinishedPlaying = () => {
                statusText.textContent = "Ready. Press 'Start Recording' to speak again.";
                startBtn.disabled = false;
                stopBtn.disabled = true;
            };
            // ------------------------------------------

            playAudioSequentially(data.audio_urls, onFinishedPlaying);

        } catch (error) {
            statusText.textContent = `Error: ${error.message}`;
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    // --- Text Input Logic ---
    async function sendTextToLlm(text) {
        statusText.textContent = "Thinking...";
        submitTextBtn.disabled = true;
        textQueryInput.value = "";
        
        try {
            // This correctly calls the conversational text endpoint
            const response = await fetch(`/agent/chat/text/${sessionId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text })
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to process text.");
            }
            const data = await response.json();

            resultsContainer.classList.remove('hidden');
            transcriptionText.textContent = `You wrote: "${data.transcription}"`;
            responseText.textContent = `Agent says: "${data.llm_response}"`;
            
            const onFinishedPlaying = () => {
                setInputMode('type');
                submitTextBtn.disabled = false;
            };
            playAudioSequentially(data.audio_urls, onFinishedPlaying);

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
        
        startBtn.disabled = true;
        stopBtn.disabled = true;
        
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

    // --- UI Mode Switching ---
    function setInputMode(mode) {
        const isSpeakMode = mode === 'speak';
        speakModeContainer.classList.toggle('hidden', !isSpeakMode);
        typeModeContainer.classList.toggle('hidden', isSpeakMode);
        switchToSpeakBtn.classList.toggle('active', isSpeakMode);
        switchToTypeBtn.classList.toggle('active', !isSpeakMode);
        statusText.textContent = isSpeakMode ? "Press 'Start Recording' to begin." : "Type your message and press send.";
        resultsContainer.classList.add('hidden');
    }

    // --- Event Listeners ---
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    submitTextBtn.addEventListener("click", () => {
        const query = textQueryInput.value.trim();
        if (query) sendTextToLlm(query);
    });
    switchToSpeakBtn.addEventListener("click", () => setInputMode('speak'));
    switchToTypeBtn.addEventListener("click", () => setInputMode('type'));
    
    // --- Initialization ---
    initializeSession();
    setInputMode('speak');
});
