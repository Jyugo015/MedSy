from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from faster_whisper import WhisperModel
from transformers import NllbTokenizer, AutoModelForSeq2SeqLM
from gtts import gTTS
import os
import uuid
import torch
import requests
from typing import Dict, Optional
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static') 
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
class Config:
    def __init__(self):
        # Model initialization
        self.whisper_model = WhisperModel("large-v2", compute_type="int8")
        
        # NLLB translation model
        nllb_model_name = "facebook/nllb-200-distilled-600M"
        self.nllb_tokenizer = NllbTokenizer.from_pretrained(nllb_model_name)
        self.nllb_model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_name)
        
        # Language support
        self.lang_code_map = {
            'en': 'eng_Latn',
            'ms': 'msa_Latn',
            'zh': 'zho_Hant',
            'zh-CN': 'zho_Hans',
            'ta': 'tam_Taml'
        }
        
        # Medical knowledge enhancement
        self.medical_terms = {
            'en-ms': {
                'heart attack': 'serangan jantung', 
                'high blood pressure': 'tekanan darah tinggi',
                'fever': 'demam'
            },
            'en-zh': {
                'heart attack': '心脏病发作 (xīnzàng bìng fāzuò)',
                'high blood pressure': '高血压 (gāo xuèyā)',
                'fever': '发烧 (fāshāo)'
            },
            'en-ta': {
                'heart attack': 'இதய நோய் தாக்குதல்',
                'high blood pressure': 'உயர் இரத்த அழுத்தம்',
                'fever': 'காய்ச்சல்'
            }
        }
        
        # LLM enhancement (optional)
        self.llm_enabled = True
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_endpoint = "mistralai/Mistral-7B-Instruct-v0.2"
        
        # Audio settings
        self.audio_output_dir = "audio_outputs"
        os.makedirs(self.audio_output_dir, exist_ok=True)

config = Config()
print(f"LLM Enabled: {config.llm_enabled}")
print(f"LLM API Key Loaded: {'Yes' if config.llm_api_key else 'No'}")

# Context Manager for conversation history
class ConversationContext:
    def __init__(self):
        self.history: Dict[str, list] = {}  # session_id -> list of messages
    
    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.history:
            self.history[session_id] = []
        self.history[session_id].append({"role": role, "content": content})
    
    def get_context(self, session_id: str, max_turns: int = 3) -> str:
        if session_id not in self.history:
            return ""
        return "\n".join(
            f"{msg['role']}: {msg['content']}" 
            for msg in self.history[session_id][-max_turns:]
        )

conversation_context = ConversationContext()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
    
# Enhanced Translation Functions
def translate_with_llm(text: str, source_lang: str, target_lang: str, session_id: str = "") -> str:
    """Enhanced translation with LLM context"""
    if not config.llm_enabled or not config.llm_api_key:
        print("⚠️ LLM translation is disabled or API key missing. Falling back to NLLB.")
        return translate_nllb(text, source_lang, target_lang)

    
    context = conversation_context.get_context(session_id)
    prompt = (
        f"You are a medical translation expert. Translate this {source_lang} text to {target_lang}, "
        f"keeping medical terms accurate. Use simple language for patient understanding.\n\n"
        f"Conversation context:\n{context}\n\n"
        f"Text to translate:\n{text}"
    )
    
    headers = {
        "Authorization": f"Bearer {config.llm_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    print("\n📡 Attempting to call OpenAI API...")
    print(f"🔑 API Key: {'*****' + config.llm_api_key[-4:] if config.llm_api_key else 'MISSING'}")
    print(f"📝 Prompt: {prompt[:200]}...")  # Print first 200 chars to avoid spam

    try:
        response = requests.post(config.llm_endpoint, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"LLM translation failed: {str(e)}")
        return translate_nllb(text, source_lang, target_lang)

def translate_nllb(text: str, source_lang: str, target_lang: str) -> str:
    """Traditional NLLB translation"""
    tokenizer = config.nllb_tokenizer
    model = config.nllb_model
    
    # Set source language
    tokenizer.src_lang = config.lang_code_map[source_lang]
    
    # Prepare inputs
    inputs = tokenizer(text, return_tensors="pt")
    
    # Get forced bos token ID for target language (correct way)
    forced_bos_token_id = tokenizer.convert_tokens_to_ids(config.lang_code_map[target_lang])
    
    # Generate translation
    output_tokens = model.generate(
        **inputs, 
        forced_bos_token_id=forced_bos_token_id,
        max_length=500
    )
    return tokenizer.decode(output_tokens[0], skip_special_tokens=True)

def enhance_medical_terms(text: str, source: str, target: str) -> str:
    """Enhance medical terminology in translation"""
    key = f"{source}-{target}"
    if key in config.medical_terms:
        for term, replacement in config.medical_terms[key].items():
            text = text.replace(term, replacement)
    return text


# API Endpoints
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.get_json()
        text = data.get('text', '')
        source_lang = data.get('source', 'en')
        target_lang = data.get('target', 'ms')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Process translation
        enhanced = enhance_medical_terms(text, source_lang, target_lang)
        conversation_context.add_message(session_id, "User", text)
        translation = translate_with_llm(enhanced, source_lang, target_lang, session_id)
        conversation_context.add_message(session_id, "System", translation)
        
        # Generate audio from the TRANSLATED text
        audio_path = generate_audio(translation, target_lang)
        print(translation)  # Debug
        print(f"Generated audio path: {audio_path}")  # Debug
        if not audio_path:
            return jsonify({'error': 'Audio generation failed'}), 500
            
        return jsonify({
            'original_text': text,
            'translated_text': translation,
            'audio_url': f"/audio/{os.path.basename(audio_path)}",
            'session_id': session_id,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
def generate_audio(text: str, lang: str) -> Optional[str]:
    try:
        # Create output directory if not exists
        os.makedirs(config.audio_output_dir, exist_ok=True)
        
        # Secure filename and path
        filename = f"{uuid.uuid4()}.mp3"
        safe_filename = secure_filename(filename)
        path = os.path.abspath(os.path.join(config.audio_output_dir, safe_filename))
        
        print(f"Attempting to generate audio to: {path}")  # Debug
        
        # Language mapping with proper gTTS codes
        lang_map = {
            'ms': 'ms',       # Malay
            'zh': 'zh',       # Chinese
            'zh-CN': 'zh',    # Chinese (alternative)
            'ta': 'ta',       # Tamil
            'en': 'en'        # English
        }
        
        tts = gTTS(
            text=text,
            lang=lang_map.get(lang, 'en'),  # Default to English
            slow=False,
            lang_check=False  # Disable strict language checking
        )
        
        tts.save(path)
        print(f"Audio successfully saved to: {path}")  # Debug
        
        # Verify file was created
        if os.path.exists(path):
            return path
        return None
        
    except Exception as e:
        print(f"Error in generate_audio: {str(e)}")
        return None

@app.route('/generate_audio', methods=['POST'])
def handle_audio_generation():
    """Dedicated endpoint for audio generation"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        lang = data.get('lang', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        audio_path = generate_audio(text, lang)
        if not audio_path:
            return jsonify({'error': 'Audio generation failed'}), 500
            
        return jsonify({
            'audio_url': f"/audio/{os.path.basename(audio_path)}",
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process_audio', methods=['POST'])
def handle_audio():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        audio_file = request.files['file']
        source_lang = request.form.get('source', 'en')
        target_lang = request.form.get('target', 'ms')
        session_id = request.form.get('session_id', str(uuid.uuid4()))
        
        # Save temporary file
        temp_path = f"/tmp/{uuid.uuid4()}.wav"
        audio_file.save(temp_path)
        
        # Transcribe
        segments, _ = config.whisper_model.transcribe(
            temp_path, 
            beam_size=5, 
            language=source_lang
        )
        transcription = " ".join([seg.text for seg in segments])
        
        # Process translation
        enhanced = enhance_medical_terms(transcription, source_lang, target_lang)
        conversation_context.add_message(session_id, "Patient", transcription)
        translation = translate_with_llm(enhanced, source_lang, target_lang, session_id)
        conversation_context.add_message(session_id, "System", translation)
        
        # Generate audio
        audio_path = generate_audio(translation, target_lang)
        
        # Clean up
        os.remove(temp_path)
        
        response = {
            'transcription': transcription,
            'translation': translation,
            'session_id': session_id
        }
        
        if audio_path:
            response['audio_url'] = f"/audio/{os.path.basename(audio_path)}"
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files with proper headers"""
    try:
        safe_filename = secure_filename(filename)
        path = os.path.join(config.audio_output_dir, safe_filename)
        
        if not os.path.exists(path):
            return jsonify({'error': 'File not found'}), 404
            
        return send_from_directory(
            config.audio_output_dir,
            safe_filename,
            mimetype='audio/mpeg',
            as_attachment=False
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test_llm')
def test_llm():
    test_text = "Hello, how are you?"
    translation = translate_with_llm(test_text, "en", "ms")
    return jsonify({"translation": translation})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)