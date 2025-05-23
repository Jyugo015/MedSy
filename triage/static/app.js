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

// Audio constraints
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

// Utility: Animate status message
function animateStatusText(baseText) {
    let dotCount = 0;
    clearInterval(animationInterval);
    animationInterval = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        recordingStatus.textContent = baseText + ".".repeat(dotCount);
    }, 300);
}

// Utility: Clear UI fields
function clearTranscription() {
    textArea.value = "";
    detectedLanguage.textContent = "-";
    wordCountElement.textContent = "0";
    summaryText.value = "";
    autoResizeTextarea(textArea);
    autoResizeTextarea(summaryText);
}

// Utility: Update UI based on recording state
function updateUIForRecording(recording) {
    startButton.disabled = recording;
    stopButton.disabled = !recording;
    pulseElement.style.opacity = recording ? '1' : '0';
    pulseElement.style.animation = recording ? 'pulse 1.5s infinite' : 'none';

    if (!recording &&
        !recordingStatus.textContent.includes("Error") &&
        !recordingStatus.textContent.includes("complete")) {
        recordingStatus.textContent = "Ready";
    }
}

// Utility: Cleanup function
function cleanup() {
    clearInterval(animationInterval);
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }

    isRecording = false;
    mediaStream = null;
    mediaRecorder = null;
    audioChunks = [];

    updateUIForRecording(false);
}

// Auto-resize utility
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto'; // Reset the height
    textarea.style.height = textarea.scrollHeight + 'px'; // Adjust to content
}

function cleanText(text) {
  // Normalize spaces
  let cleaned = text.replace(/ +/g, ' ');

  // Insert section titles with 2 line breaks after them
  const sections = [
    "Patient Summary:",
    "Potential Causes:",
    "Recommended Diagnostic Tests:",
    "Immediate Management Suggestions:",
    "When to Seek Urgent Care:"
  ];

  sections.forEach(section => {
    const regex = new RegExp(section, 'gi');
    cleaned = cleaned.replace(regex, '\n' + section + '\n\n');
  });

  // Add a line break before each numbered point (1., 2., 3.) with one empty line before
  cleaned = cleaned.replace(/(\d+)\.\s*/g, '\n$1. ');

  // Only add a line break before hyphens used as bullet points (start of line or after newline/space)
  cleaned = cleaned.replace(/(?:\n|\r|^)-\s+/g, '\n- ');

  // Remove line breaks in the middle of broken phrases (e.g., over \n the \n counter)
  cleaned = cleaned.replace(/([a-z])\n([a-z])/gi, '$1 $2');

  // Replace multiple newlines with just two
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  // Trim final output
  return cleaned.trim();
}

// Optionally support auto-resizing on user edits
textArea.addEventListener('input', () => autoResizeTextarea(textArea));
summaryText.addEventListener('input', () => autoResizeTextarea(summaryText));

// Start Recording Handler
startButton.addEventListener('click', async () => {
    if (isRecording) return;

    try {
        isRecording = true;
        updateUIForRecording(true);
        clearTranscription();
        recordingStatus.textContent = "Initializing...";
        audioChunks = [];

        mediaStream = await navigator.mediaDevices.getUserMedia(audioConstraints);
        updateUIForRecording(true);

        const audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);
        const destination = audioContext.createMediaStreamDestination();

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

        animateStatusText("Recording");
        mediaRecorder.start(250);

    } catch (error) {
        console.error("Recording Error:", error);
        recordingStatus.textContent = `Recording Error: ${error.message}`;
        summaryText.value = "Failed to start recording. Check microphone permissions.";
        autoResizeTextarea(summaryText);
        cleanup();
    }
});

// Stop Recording Handler
stopButton.addEventListener('click', async () => {
    if (!isRecording) return;

    isRecording = false;
    updateUIForRecording(false);
    animateStatusText("Processing");
    recordingStatus.textContent = "Processing...";

    try {
        mediaRecorder.stop();
        await new Promise(resolve => mediaRecorder.onstop = resolve);
        mediaStream.getTracks().forEach(track => track.stop());

        if (audioChunks.length === 0) {
            throw new Error("No audio was recorded");
        }

        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        clearInterval(animationInterval);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || errorData.details || response.statusText;
            throw new Error(`Server Error: ${errorMsg}`);
        }

        const result = await response.json();

        textArea.value = result.transcription || "[No transcription]";
        autoResizeTextarea(textArea);

        detectedLanguage.textContent = result.language || "-";
        wordCountElement.textContent = result.word_count || "0";

        summaryText.value = cleanText(result.medical_analysis || "[No analysis]");
        autoResizeTextarea(summaryText);

        recordingStatus.textContent = "Analysis complete!";

    } catch (error) {
        clearInterval(animationInterval);
        console.error("Processing Error:", error);

        if (error.message.includes("No audio")) {
            recordingStatus.textContent = "Error: No audio detected";
            summaryText.value = "Please speak louder or check your microphone.";
        } else if (error.message.includes("Server Error")) {
            recordingStatus.textContent = "Server Error";
            summaryText.value = "Failed to process audio. Please try again later.";
        } else {
            recordingStatus.textContent = "Processing Error";
            summaryText.value = error.message || "An unknown error occurred";
        }

        autoResizeTextarea(summaryText);

    } finally {
        cleanup();
    }
});