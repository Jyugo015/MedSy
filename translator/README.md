# MedSy
This project is a Flask-based web application that uses Whisper, NLLB/LLMs, and gTTS to:
- Transcribe speech using Whisper.
- Translate text between languages with enhanced medical terminology support.
- Generate spoken audio from the translated text.

Supported Languages:
English (en), Malay (ms), Chinese (Traditional and Simplified) (zh, zh-CN), Tamil (ta)

## Initial Setup
Python version required: Python 3.10
This repo contains all the necessary files to run the MedSy multilingual translator.

$ git clone https://github.com/your-username/medsy.git

$ cd medsy

$ cd translator

$ python310 -m venv venv

$ source venv/bin/activate # For Windows: venv\Scripts\activate

## Install dependencies
(venv) $ pip install Flask faster-whisper transformers torch gtts python-dotenv

## Add environment variables
LLM_API_KEY=XXX

## Run the Flask server
(venv) $ python app.py

