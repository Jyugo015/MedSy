# MedSy
This project is a Flask-based web application that uses Whisper and Mistral-7B to:
- Transcribe patient speech using Whisper ASR
- Generate structured medical analysis using Mistral-7B
- Provide clear recommendations including potential causes and urgent care indicators

## Initial Setup
Python version required: Python 3.10
This repo contains all necessary files to run the MedSy Medical Voice Assistant.

$ git clone https://github.com/your-username/medsy.git

$ cd medsy

$ cd triage

$ python310 -m venv venv

$ source venv/bin/activate # For Windows: venv\Scripts\activate

## Install dependencies
(venv) $ pip install -r requirements.txt  

## Run the Flask server
(venv) $ python app.py

