from flask import Flask, render_template, request, jsonify
from faster_whisper import WhisperModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import subprocess
import os
from typing import Dict, Any

app = Flask(__name__)

class Config:
    WHISPER_MODEL_SIZE = "medium"
    LLM_MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
    AUDIO_SAMPLE_RATE = 16000
    MAX_RESPONSE_TOKENS = 250
    TEMPERATURE = 0.7

# === Whisper ASR Setup ===
whisper_model = WhisperModel(
    Config.WHISPER_MODEL_SIZE,
    device="cuda" if torch.cuda.is_available() else "cpu",
    compute_type="float16" if torch.cuda.is_available() else "int8",
    cpu_threads=4
)
print("Whisper model loaded successfully")

# === Mistral-7B Setup ===
print(f"Loading tokenizer for {Config.LLM_MODEL_NAME}...")
try:
    tokenizer = AutoTokenizer.from_pretrained(
        Config.LLM_MODEL_NAME,
        use_fast=False  # Changed to False to avoid tokenizer issues
    )
    print("Tokenizer loaded successfully")
except Exception as e:
    print(f"Failed to load tokenizer: {e}")
    tokenizer = None
    model = None
else:
    print("Loading Mistral model...")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            Config.LLM_MODEL_NAME,
            device_map="cpu",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        print("Mistral model loaded successfully")
    except Exception as e:
        print(f"Failed to load model: {e}")
        model = None

# === Audio Processing ===
def convert_to_wav(input_path: str, output_path: str) -> None:
    """Optimized audio conversion"""
    subprocess.run([
        'ffmpeg', '-y', '-i', input_path,
        '-ar', str(Config.AUDIO_SAMPLE_RATE),
        '-ac', '1',
        '-sample_fmt', 's16',
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def transcribe_audio(wav_path: str) -> Dict[str, Any]:
    """Fast transcription with repetition handling"""
    segments, info = whisper_model.transcribe(
        wav_path,
        language="en",
        vad_filter=False,
        beam_size=5,
        temperature=0.0
    )
    
    transcription = " ".join(segment.text for segment in segments)
    return {
        "text": transcription,
        "language": info.language,
        "duration": sum(segment.duration for segment in segments)
    }

def generate_medical_response(transcription: str) -> str:
    """Generate medical response using Mistral-7B"""
    if not model or not tokenizer:
        return "Error: Model not loaded properly"
    
    print("\nGenerating medical response...")
    
    prompt = f"""<s>[INST] You are an experienced medical assistant. Analyze this patient report and provide:
1. Summary of the patient's symptom
2. 2-3 most likely potential causes
3. Recommended diagnostic tests
4. Immediate management suggestions
5. When to seek urgent care

Patient Report:
{transcription}

Structure your response with clear headings for each section. Use simple language the patient can understand.[/INST]"""
    
    try:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
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
        return response.split("[/INST]")[-1].strip()
    except Exception as e:
        print(f"Error generating response: {e}")
        return f"Error generating medical analysis: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Create temp files
        webm_path = "temp_input.webm"
        wav_path = "temp_output.wav"
        audio_file.save(webm_path)

        # Process audio
        convert_to_wav(webm_path, wav_path)
        transcription_result = transcribe_audio(wav_path)
        medical_analysis = generate_medical_response(transcription_result["text"])

        # Cleanup
        for file_path in [webm_path, wav_path]:
            if os.path.exists(file_path):
                os.remove(file_path)

        return jsonify({
            "transcription": transcription_result["text"],
            "language": transcription_result["language"],
            "duration": transcription_result["duration"],
            "word_count": len(transcription_result["text"].split()),
            "medical_analysis": medical_analysis
        })

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({
            "error": "An error occurred during processing",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )


# from flask import Flask, render_template, request, jsonify
# from faster_whisper import WhisperModel
# import subprocess
# import torch
# import os
# from typing import Dict, Any

# app = Flask(__name__)

# class Config:
#     WHISPER_MODEL_SIZE = "medium"
#     AUDIO_SAMPLE_RATE = 16000

# # Load Whisper model
# whisper_model = WhisperModel(
#     Config.WHISPER_MODEL_SIZE,
#     device="cpu",
#     compute_type="int8" if torch.cuda.is_available() else "float32"
# )
# print("Whisper model loaded successfully")

# # === Audio Processing ===
# def convert_to_wav(input_path: str, output_path: str) -> None:
#     """Enhanced audio preprocessing"""
#     subprocess.run([
#         'ffmpeg', '-y', '-i', input_path,
#         '-ar', str(Config.AUDIO_SAMPLE_RATE),
#         '-ac', '1',
#         '-af', 'highpass=f=100,lowpass=f=4000,areverse,apad=pad_dur=0.1,areverse',
#         '-sample_fmt', 's16',
#         output_path
#     ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# def transcribe_audio(wav_path: str) -> Dict[str, Any]:
#     """Transcribe audio using faster-whisper"""
#     segments, info = whisper_model.transcribe(
#         wav_path,
#         language="en",
#         vad_filter=False,
#         beam_size=5
#     )
    
#     transcription = " ".join(segment.text for segment in segments)
    
#     # Remove duplicate sentences
#     sentences = [s.strip() for s in transcription.split('.') if s.strip()]
#     unique_sentences = []
#     seen = set()
    
#     for sentence in sentences:
#         key = sentence[:60]
#         if key not in seen:
#             seen.add(key)
#             unique_sentences.append(sentence)
    
#     return {
#         "text": '. '.join(unique_sentences) + ('.' if unique_sentences else ''),
#         "language": info.language,
#         "duration": sum(segment.duration for segment in segments)
#     }

# # === Web Routes ===
# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/analyze', methods=['POST'])
# def analyze_audio():
#     try:
#         print("\n=== New Audio Request ===")
#         if 'audio' not in request.files:
#             return jsonify({"error": "No audio file provided"}), 400

#         audio_file = request.files['audio']
#         if audio_file.filename == '':
#             return jsonify({"error": "No selected file"}), 400

#         # Create temp files
#         webm_path = "temp_input.webm"
#         wav_path = "temp_output.wav"
#         audio_file.save(webm_path)

#         # Process audio
#         convert_to_wav(webm_path, wav_path)
#         transcription_result = transcribe_audio(wav_path)
        
#         # Mocked analysis response
#         medical_analysis = '''
#         \tPatient Symptoms:
#         - High blood sugar readings for the past two weeks
#         - Increased thirst
#         - Frequent urination, especially at night
#         - Taking diabetes medication with little effect

#         Potential Causes:
#         1. Poorly controlled diabetes or medication resistance
#         2. Potential onset of diabetic complications
#         3. Dehydration due to high blood sugar levels

#         Recommended Diagnostic Tests:
#         - Fasting Blood Glucose Test
#         - HbA1c Test
#         - Urinalysis for ketones and glucose

#         Immediate Management Suggestions:
#         - Monitor blood sugar levels more frequently
#         - Increase water intake
#         - Review medication dosage
#         - Consider dietary adjustments

#         When to Seek Urgent Care:
#         - Persistent blood sugar readings above 250 mg/dL
#         - Symptoms of diabetic ketoacidosis
#         - Severe dehydration or confusion
#         '''

#         # Cleanup
#         for file_path in [webm_path, wav_path]:
#             if os.path.exists(file_path):
#                 os.remove(file_path)

#         return jsonify({
#             "transcription": transcription_result["text"],
#             "language": transcription_result["language"],
#             "duration": transcription_result["duration"],
#             "word_count": len(transcription_result["text"].split()),
#             "medical_analysis": medical_analysis.strip()
#         })

#     except Exception as e:
#         print(f"Error processing request: {str(e)}")
#         return jsonify({
#             "error": "An error occurred during processing",
#             "details": str(e)
#         }), 500

# if __name__ == "__main__":
#     print("Starting Flask server...")
#     app.run(
#         host='0.0.0.0',
#         port=5000,
#         debug=True,
#         threaded=True
#     )