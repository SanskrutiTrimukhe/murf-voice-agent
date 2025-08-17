document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Element References ---
    const startBtn = document.getElementById("startRecording");
    const stopBtn = document.getElementById("stopRecording");
    const statusText = document.getElementById("statusText");
    
    // --- State Variables ---
    let mediaRecorder;
    let websocket; // WebSocket object

    // --- Main Functions for Streaming ---

    async function startRecording() {
        // 1. Establish WebSocket Connection
        // Use wss:// for production environments
        const wsUrl = `ws://127.0.0.1:8000/ws`;
        websocket = new WebSocket(wsUrl);

        websocket.onopen = async () => {
            console.log("WebSocket connection established for streaming.");
            statusText.textContent = "Connecting to microphone...";
            
            // 2. Get Microphone Access (after WS is open)
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                // 3. Configure MediaRecorder to stream data
                // The timeslice parameter triggers ondataavailable every X milliseconds
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
                        // Send the audio chunk over the WebSocket as it becomes available
                        websocket.send(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    console.log("Recording stopped by user.");
                    // Gracefully close the WebSocket connection when recording stops
                    if (websocket.readyState === WebSocket.OPEN) {
                        websocket.close();
                    }
                    // Stop the microphone stream to release the resource
                    stream.getTracks().forEach(track => track.stop());
                    
                    // Reset UI
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    statusText.textContent = "Recording sent. Ready for next one.";
                };
                
                websocket.onclose = () => {
                    console.log("WebSocket connection closed.");
                };

                websocket.onerror = (error) => {
                    console.error("WebSocket Error:", error);
                    statusText.textContent = "Error with WebSocket connection.";
                };

                // Start recording with a timeslice to get chunks periodically
                mediaRecorder.start(500); // Create an audio chunk every 500ms
                
                // Update UI
                startBtn.disabled = true;
                stopBtn.disabled = false;
                statusText.textContent = "Streaming audio... 🔴";

            } catch (error) {
                console.error("Error accessing microphone:", error);
                statusText.textContent = "Could not access microphone. Please grant permission.";
                // Close the WebSocket if microphone access fails
                if (websocket.readyState === WebSocket.OPEN) {
                    websocket.close();
                }
            }
        };
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
    }

    // --- Event Listeners ---
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    
    // Initialize UI state
    stopBtn.disabled = true;
    statusText.textContent = "Press 'Start Recording' to begin streaming.";
});
