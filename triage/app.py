import os
import tempfile
import time
import re
from typing import Dict, Any
import torch
from torch import amp
from flask import Flask, jsonify, render_template, request
# from faster_whisper import WhisperModel
import whisper
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# --- Configuration ---
class Config:
    # Model configurations
    WHISPER_MODEL_SIZE = "turbo"  
    # LLM_MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
    LLM_MODEL_NAME = "arcee-ai/BioMistral-merged-instruct"
    
    # Quantization settings
    LOAD_IN_4BIT = True  # Critical for memory efficiency
    BNB_4BIT_COMPUTE_DTYPE = torch.float16
    
    # Audio processing
    AUDIO_SAMPLE_RATE = 16000
    USE_VAD = False  
    
    # Generation parameters
    MAX_RESPONSE_TOKENS = 1200
    TEMPERATURE = 0.3
    
    # Hardware settings
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    WHISPER_COMPUTE_TYPE = "int8_float16" if torch.cuda.is_available() else "int8"

# --- Initialize Flask App ---
app = Flask(__name__)

# --- Load Models with Error Handling ---
def load_models():
    """Load models with proper error handling and resource management"""
    models = {}
    
    try:
        # Configure quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=Config.LOAD_IN_4BIT,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=Config.BNB_4BIT_COMPUTE_DTYPE,
            bnb_4bit_use_double_quant=True
        ) if Config.LOAD_IN_4BIT and torch.cuda.is_available() else None

        # Load LLM First (the bottleneck)
        print(f"Loading {Config.LLM_MODEL_NAME}...")
        models['llm'] = {
            'tokenizer': AutoTokenizer.from_pretrained(
                Config.LLM_MODEL_NAME,
                use_fast=False
            ),
            'model': AutoModelForCausalLM.from_pretrained(
                Config.LLM_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
        }
        print("✓ LLM loaded successfully")

        # Then load Whisper
        print(f"Loading Whisper ({Config.WHISPER_MODEL_SIZE})...")
        # models['whisper'] = WhisperModel(
        #     Config.WHISPER_MODEL_SIZE,
        #     device="cuda" if torch.cuda.is_available() else "cpu",
        #     compute_type=Config.WHISPER_COMPUTE_TYPE,
        #     download_root="./whisper_models",
        #     cpu_threads=4 if Config.DEVICE == "cpu" else 0
        # )
        models['whisper'] = whisper.load_model(Config.WHISPER_MODEL_SIZE).to(Config.DEVICE)
        print("✓ Whisper loaded successfully")

    except Exception as e:
        print(f"Error loading models: {e}")
        models['whisper'] = None
        models['llm'] = None

    return models

# --- Transcription Function ---
def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """Optimized transcription with performance monitoring"""
    if not models.get('whisper'):
        raise RuntimeError("Whisper model not loaded")
    
    start_time = time.time()

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        
        result = models['whisper'].transcribe(audio_path, fp16=torch.cuda.is_available())
        transcription = result.get("text", "").strip()

        return {
            "text": transcription,
            "language": result.get("language", "unknown"),
            "duration": result.get("duration", 0),
            "processing_time": time.time() - start_time,
            "word_count": len(transcription.split())
        }

        # segments, info = models['whisper'].transcribe(
        #     audio_path,
        #     language=None,
        #     beam_size=3,
        #     vad_filter=Config.USE_VAD,
        #     without_timestamps=True
        # )

        # transcription = " ".join(segment.text.strip() for segment in segments).strip()

        # if not transcription:
        #     return {
        #         "text": "",
        #         "language": info.language,
        #         "duration": info.duration,
        #         "processing_time": time.time() - start_time,
        #         "word_count": 0
        #     }

        # return {
        #     "text": transcription,
        #     "language": info.language,
        #     "duration": info.duration,
        #     "processing_time": time.time() - start_time,
        #     "word_count": len(transcription.split())
        # }

    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise RuntimeError(f"Transcription failed: {str(e)}")

# --- Medical Response Generation ---
def generate_medical_response(transcription: str) -> str:
    """Generate structured medical response with error handling"""
    if not models.get('llm'):
        return "Error: LLM model not loaded properly"

    prompt = f"""<s>[INST] You are a clinical triage assistant. Your job is to read a patient report and determine:

STEP 1: Does the report contain any **explicit medical symptoms or complaints** such as pain, fever, cough, nausea, fatigue, etc?

- If NO symptoms or medical complaints are found, output ONLY:
"This report does not appear to be a valid medical input. Please provide a health-related description."

- If YES, then proceed to STEP 2.

STEP 2: Follow this exact structure and limit each list to **3 items maximum**:

Patient Symptoms:
- [Symptom 1]
- [Symptom 2]

Differential Diagnoses (Possible Causes):
1. [Cause 1 — reason]
2. [Cause 2 — reason]
3. [Optional Cause 3 — reason]

Recommended Diagnostic Tests:
1. [Test 1 — reason]
2. [Test 2 — reason]
3. [Test 3 — reason]

Immediate Management Recommendations:
1. [Action 1]
2. [Action 2]
3. [Action 3]

When to Seek Medical Attention:
1. Emergency care: [Condition]
2. Urgent care within 24h: [Condition]
3. Self-care appropriate: [Condition]

Make sure to include **ALL** sections fully, even if some items are placeholders.

Patient Report:
{transcription}
[/INST]"""


#     prompt = f"""<s>[INST]
# You are a clinical triage assistant. Read the patient report and extract the following in markdown format.

# If no clear symptoms are found, respond with:
# "This report does not appear to be a valid medical input. Please provide a health-related description."

# Otherwise, extract:

# ### Patient Symptoms:
# - Symptom 1
# - Symptom 2
# - ...

# ### Differential Diagnoses (Possible Causes):
# 1. Cause 1 — brief reason
# 2. Cause 2 — brief reason

# ### Recommended Diagnostic Tests:
# 1. Test 1 — reason
# 2. Test 2 — reason

# ### Immediate Management Recommendations:
# 1. Recommendation 1
# 2. Recommendation 2

# ### When to Seek Medical Attention:
# - Emergency care if: [Condition]
# - Urgent care within 24h if: [Condition]
# - Self-care appropriate if: [Condition]

# Now, analyze this:
# {transcription}
# [/INST]</s>"""


    try:
        tokenizer = models['llm']['tokenizer']
        model = models['llm']['model']
        
        inputs = tokenizer(prompt, return_tensors="pt").to(Config.DEVICE)
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        with torch.no_grad(), amp.autocast(device_type='cuda' if torch.cuda.is_available() else 'cpu'):
            outputs = model.generate(
                **inputs,
                max_new_tokens=Config.MAX_RESPONSE_TOKENS,
                temperature=Config.TEMPERATURE,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                no_repeat_ngram_size=3
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        clean_response = postprocess_output(response.split("[/INST]")[-1].strip())
        return clean_response

    except Exception as e:
        print(f"Error generating response: {e}")
        return f"Error generating medical analysis: {str(e)}"

def postprocess_output(text: str) -> str:
    # Keep markdown bullets like "-", but clean up extra asterisks or headers
    text = re.sub(r"[*_#]", "", text)  
    
    # Normalize excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    
    # Ensure consistent line breaks after bullets and numbers
    text = re.sub(r"(?<=\S)\n(?=[^-•0-9])", " ", text)  # Join broken lines unless it's clearly a bullet or number
    
    return text.strip()


# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')



@app.route('/analyze', methods=['POST'])
def analyze_audio():
    """Endpoint for audio analysis with proper resource cleanup"""
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            audio_path = tmp.name
            request.files['audio'].save(audio_path)

        transcription_result = transcribe_audio(audio_path)

        # If no transcription was produced, stop here
        if not transcription_result["text"]:
            return jsonify({
                "transcription": "",
                "language": transcription_result["language"],
                "duration": transcription_result["duration"],
                "processing_time": transcription_result["processing_time"],
                "word_count": 0,
                "medical_analysis": "No speech was detected in the audio. Please try again with a clear spoken input."
            })

        # Proceed with medical response generation
        medical_analysis = generate_medical_response(transcription_result["text"])
        
        return jsonify({
            "transcription": transcription_result["text"],
            "language": transcription_result["language"],
            "duration": transcription_result["duration"],
            "processing_time": transcription_result["processing_time"],
            "word_count": transcription_result["word_count"],
            "medical_analysis": medical_analysis
        })

    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as e:
                print(f"Error cleaning up temp file: {e}")

# --- Server Startup ---
if __name__ == "__main__":
    # Check for VAD support
    try:
        import onnxruntime
        Config.USE_VAD = True
        print("✓ onnxruntime found - VAD enabled")
    except ImportError:
        print("✗ onnxruntime not found - install with: pip install onnxruntime")

    # Initialize models
    print("\nInitializing models...")
    torch.backends.cuda.enable_flash_sdp(True)  # Enable flash attention if available
    models = load_models()
    
    # Start server
    print("\nStarting Flask server...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Disabled for production
        threaded=True
    )
    