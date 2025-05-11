let mediaStream;
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let animationInterval;

// DOM elements
const startButton = document.getElementById('startRecording');
const stopButton = document.getElementById('stopRecording');
const textArea = document.getElementById('transcriptionResult');
const detectedLanguage = document.getElementById('detectedLanguage');
const recordingStatus = document.getElementById('recordingStatus');
const wordCountElement = document.getElementById('wordCount');
const summaryText = document.getElementById('medicalSummary');
const pulseElement = document.querySelector('.pulse');

// Audio constraints for better quality
const audioConstraints = {
    audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 16000,
        channelCount: 1,
        sampleSize: 16,
        autoGainControl: true
    }
};

// Animation helper function
function animateStatusText(baseText) {
    let dotCount = 0;
    clearInterval(animationInterval);
    animationInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        recordingStatus.textContent = baseText + ".".repeat(dotCount);
    }, 300);
}

// Start Recording
startButton.addEventListener('click', async () => {
    if (isRecording) return;

    try {
        isRecording = true;
        updateUIForRecording(true);
        clearTranscription();
        audioChunks = [];

        // Get high quality audio
        mediaStream = await navigator.mediaDevices.getUserMedia(audioConstraints);

        // Create audio context for processing
        const audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);
        const destination = audioContext.createMediaStreamDestination();

        // Simple noise gate
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
            const input = e.inputBuffer.getChannelData(0);
            const output = e.outputBuffer.getChannelData(0);
            for (let i = 0; i < input.length; i++) {
                output[i] = Math.abs(input[i]) > 0.02 ? input[i] : 0;
            }
        };

        source.connect(processor);
        processor.connect(destination);

        mediaRecorder = new MediaRecorder(destination.stream);

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        // Start recording animation
        animateStatusText("Recording");
        mediaRecorder.start(250);
    } catch (error) {
        console.error('Error:', error);
        recordingStatus.textContent = `Error: ${error.message}`;
        cleanup();
    }
});

// Stop and process - UPDATED VERSION
stopButton.addEventListener('click', async () => {
    if (!isRecording) return;

    // First stop the recording
    mediaRecorder.stop();
    
    // Set up a promise to handle the final data
    const recordingStopped = new Promise(resolve => {
        mediaRecorder.onstop = resolve;
    });

    // Wait for recording to fully stop
    await recordingStopped;
    
    // Stop all media tracks
    mediaStream.getTracks().forEach(track => track.stop());

    try {
        // Show processing status
        animateStatusText("Processing");
        
        // Verify we have audio data
        if (audioChunks.length === 0) {
            throw new Error("No audio recorded");
        }

        // Create and send the audio blob
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        console.log("Sending audio to server...");
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        // Clear the loading animation
        clearInterval(animationInterval);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error: ${errorText}`);
        }

        const result = await response.json();
        console.log("Server response:", result);

        if (result.error) {
            throw new Error(result.error);
        }

        // Update the UI with results
        textArea.value = result.transcription || "[No transcription]";
        detectedLanguage.textContent = result.language || "-";
        wordCountElement.textContent = result.word_count || "0";
        summaryText.textContent = result.medical_analysis || "[No analysis]";
        recordingStatus.textContent = "Analysis complete!";

    } catch (error) {
        console.error("Processing error:", error);
        recordingStatus.textContent = `Error: ${error.message}`;
        summaryText.textContent = "Failed to generate analysis. Please try again.";
    } finally {
        // Only reset the recording state, don't fully clean up
        isRecording = false;
        updateButtonStates();
    }
});

// Updated cleanup function
function cleanup() {
    // Only reset basic recording state
    isRecording = false;
    clearInterval(animationInterval);
    
    // Don't reset UI if we're showing results or errors
    if (!recordingStatus.textContent.includes("complete") && 
        !recordingStatus.textContent.includes("Error")) {
        updateUIForRecording(false);
    }
}

// Updated UI update function
function updateUIForRecording(recording) {
    startButton.disabled = recording;
    stopButton.disabled = !recording;
    pulseElement.style.opacity = recording ? '1' : '0';
    pulseElement.style.animation = recording ? 'pulse 1.5s infinite' : 'none';
    
    // Only update status if not in a completed state
    if (!recording && 
        !recordingStatus.textContent.includes("complete") &&
        !recordingStatus.textContent.includes("Error")) {
        recordingStatus.textContent = "Ready";
    }
}

function clearTranscription() {
    textArea.value = "";
    detectedLanguage.textContent = "-";
    wordCountElement.textContent = "0";
    summaryText.textContent = "";
}