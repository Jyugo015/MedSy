const config = {
  apiUrl: "http://localhost:5000",
  speechRecognition: window.SpeechRecognition || window.webkitSpeechRecognition,
};

// DOM Elements
const elements = {
  recordBtn: document.getElementById("recordBtn"),
  stopBtn: document.getElementById("stopBtn"),
  uploadBtn: document.getElementById("uploadBtn"),
  audioUpload: document.getElementById("audioUpload"),
  sourceLang: document.getElementById("sourceLang"),
  targetLang: document.getElementById("targetLang"),
  originalText: document.getElementById("originalText"),
  inputText: document.getElementById("inputText"),
  translation: document.getElementById("translation"),
  error: document.getElementById("error"),
  audioContainer: document.getElementById("audioContainer"),
  audioPlayer: document.getElementById("audioPlayer"),
};

// Initialize speech recognition
let recognition;
if (config.speechRecognition) {
  recognition = new config.speechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = elements.sourceLang.value;

  // Modify your recognition setup
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    elements.inputText.value = transcript;
    // Add this to ensure we wait for the final result
    if (event.results[0].isFinal) {
      translateText(transcript);
    }
  };

  recognition.onerror = (event) => {
    showError(`Speech recognition error: ${event.error}`);
  };

  recognition.onend = () => {
    // Only re-enable buttons if not recording
    elements.recordBtn.disabled = false;
    elements.stopBtn.disabled = true;
  };
} else {
  showError("Speech recognition not supported in your browser");
  elements.recordBtn.disabled = true;
}

// Event Listeners
elements.recordBtn.addEventListener("click", startRecording);
elements.stopBtn.addEventListener("click", stopRecording);
elements.uploadBtn.addEventListener("click", () =>
  elements.audioUpload.click()
);
elements.audioUpload.addEventListener("change", handleAudioUpload);
elements.sourceLang.addEventListener("change", updateRecognitionLanguage);
elements.inputText.addEventListener("input", () => {
  if (elements.inputText.value) {
    translateText(elements.inputText.value);
  } else {
    elements.translation.textContent = "";
    elements.audioContainer.style.display = "none";
  }
});

// Functions
function startRecording() {
  clearError();
  recognition.lang = elements.sourceLang.value;
  recognition.start();
  elements.recordBtn.disabled = true;
  elements.stopBtn.disabled = false;
  elements.inputText.placeholder = "Listening...";
}

function stopRecording() {
  recognition.stop();
  elements.inputText.placeholder = "Enter text or speak to translate...";
}

function updateRecognitionLanguage() {
  recognition.lang = elements.sourceLang.value;
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.style.display = "block";
}

function clearError() {
  elements.error.textContent = "";
  elements.error.style.display = "none";
}

async function handleAudioUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  clearError();
  showLoading("Processing audio...");

  const formData = new FormData();
  formData.append("file", file);
  formData.append("source", elements.sourceLang.value);
  formData.append("target", elements.targetLang.value);

  try {
    const response = await fetch(`${config.apiUrl}/process_audio`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Audio processing failed");
    }

    const data = await response.json();
    elements.inputText.value = data.transcription;
    elements.translation.textContent = data.translation;

    if (data.audio_url) {
      elements.audioPlayer.src = data.audio_url;
      elements.audioContainer.style.display = "block";
    }
  } catch (err) {
    showError(`Error: ${err.message}`);
    console.error("Audio processing error:", err);
  } finally {
    event.target.value = ""; // Reset file input
  }
}

function showLoading(message) {
  elements.translation.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `;
}
async function translateText(text) {
  if (!text.trim()) {
    elements.translation.textContent = "";
    elements.audioContainer.style.display = "none";
    return;
  }

  console.log("Starting translation for:", text); // DEBUG 1

  clearError();
  showLoading("Translating...");

  try {
    console.log("Making request to:", `${config.apiUrl}/translate`); // DEBUG 2

    const response = await fetch(`${config.apiUrl}/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        source: elements.sourceLang.value,
        target: elements.targetLang.value,
      }),
    });

    console.log("Received response, status:", response.status); // DEBUG 3

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Server error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    console.log("Response data:", data); // DEBUG 4

    // SAFETY CHECK - ensure we have the translated text
    if (!data.translated_text && !data.translation) {
      throw new Error("No translation found in response");
    }

    const translatedText = data.translated_text || data.translation;
    console.log("Setting translation to:", translatedText); // DEBUG 5

    elements.translation.textContent = translatedText;
    console.log("Element content should be updated now"); // DEBUG 6

    await generateAndPlayAudio(translatedText);
  } catch (err) {
    console.error("TRANSLATION ERROR:", err); // DEBUG 7
    elements.translation.textContent = "Error: " + err.message;
  }
}

async function generateAndPlayAudio(text) {
  // Clear previous audio elements
  const audioContainer = document.getElementById("audioContainer");
  audioContainer.innerHTML = '<div class="loading">Generating audio...</div>';

  try {
    const response = await fetch(`${config.apiUrl}/generate_audio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang: elements.targetLang.value }),
    });

    if (!response.ok) throw new Error("Audio generation failed");
    const { audio_url } = await response.json();

    // Create SINGLE audio element
    const audioHTML = `
      <audio controls autoplay id="translationAudio" 
             onerror="this.parentElement.innerHTML='<p>Playback failed</p>'">
        <source src="${audio_url}?t=${Date.now()}" type="audio/mpeg">
      </audio>
    `;
    audioContainer.innerHTML = audioHTML;
  } catch (err) {
    audioContainer.innerHTML = `<p class="error">${err.message}</p>`;
  }
}

async function sendTranslationRequest() {
  const text = document.getElementById("inputText").value;
  const targetLang = document.getElementById("targetLang").value;

  try {
    const response = await fetch("/translate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        target: targetLang,
      }),
    });

    const data = await response.json();

    if (data.error) {
      console.error("Error:", data.error);
      document.getElementById("resultText").textContent =
        "Error: " + data.error;
      return;
    }

    // Display both original and translated text
    document.getElementById("originalText").value = data.original_text;
    document.getElementById("translatedText").textContent =
      data.translated_text;

    // Play the translated audio
    const audioPlayer = document.getElementById("audioPlayer");
    audioPlayer.src = data.audio_url;
    audioPlayer.style.display = "block";
    audioPlayer.play();
  } catch (error) {
    console.error("Translation failed:", error);
    document.getElementById("resultText").textContent =
      "Translation failed. Please try again.";
  }
}
