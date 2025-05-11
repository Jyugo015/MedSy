# WhatsApp Medical Appointment Assistant (Chatbot)

A conversational AI assistant that helps users book medical appointments via WhatsApp, using Twilio for messaging and Mistral-7B LLM for natural language processing.

## Features

- Symptom-based department recommendation
- Multi-step appointment booking flow
- Natural language interaction using Mistral-7B
- Appointment confirmation with file storage
- Local testing mode
- WhatsApp integration via Twilio

## Prerequisites

Before setup, ensure you have:

1. Python 3.8+
2. NVIDIA GPU with CUDA support (for LLM)
3. Twilio account with WhatsApp Sandbox access
4. Hugging Face account (for Mistral-7B access)

## Detailed Setup Instructions

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or 
venv\Scripts\activate  # Windows

# Install dependencies
pip install flask twilio transformers torch accelerate bitsandbytes
```

### 2. Twilio Configuration

1. Sign up at [Twilio](https://www.twilio.com/)
2. Get your Account SID and Auth Token from the dashboard
3. Enable WhatsApp Sandbox:
   - Go to WhatsApp in Twilio Console
   - Follow instructions to join the sandbox
   - Note your sandbox number (typically `whatsapp:+14155238886`)

### 3. Environment Variables

Create a `.env` file:

```ini
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### 4. Hugging Face Setup

1. Create an account at [Hugging Face](https://huggingface.co/)
2. Get your access token from Settings → Access Tokens
3. Accept the terms for Mistral-7B model usage
4. Run this command to authenticate:

```bash
huggingface-cli login
```

### 5. Directory Structure

Ensure your project has this structure:

```
project/
├── app.py               # Main application file
├── .env                 # Environment variables
├── requirements.txt     # Python dependencies
└── appointments/        # Will be created automatically
```

### 6. Running the Application

#### Development Mode:

```bash
python app.py
```

#### Production Mode (with Gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Local Testing:

```bash
python app.py --local
```

### 7. Ngrok Setup (for local development)

1. Download ngrok from https://ngrok.com/
2. Run ngrok to expose your local server:

```bash
ngrok http 5000
```

3. Configure Twilio webhook to point to your ngrok URL (e.g., `https://your-ngrok-url.ngrok.io/webhook`)

## Configuration Options

You can customize these parameters in the code:

- `model_name`: Change to other Hugging Face models
- `max_new_tokens`: Adjust response length
- Department mappings in `department_map`
- Appointment storage location (default: `appointments/` folder)

## Usage Flow

1. User sends any message to WhatsApp number
2. Bot asks about symptoms
3. Based on symptoms, suggests a department
4. Guides through appointment booking:
   - Confirmation
   - Time selection
   - Name collection
5. Stores appointment details in a text file
6. Sends confirmation message

## Troubleshooting

### Common Issues

1. **CUDA Errors**:
   - Verify `torch.cuda.is_available()` returns True
   - Ensure proper NVIDIA drivers are installed

2. **Model Loading Issues**:
   - Check Hugging Face token is valid
   - Verify you have accepted the model terms

3. **Twilio Webhook Errors**:
   - Ensure ngrok is running if testing locally
   - Verify the webhook URL in Twilio console

4. **Memory Issues**:
   - Reduce model size (use 4-bit quantization)
   - Add `load_in_4bit=True` to model loading

## Deployment Options

### 1. Cloud Providers

- **AWS**: Use EC2 (g4dn.xlarge or larger) with Elastic IP
- **Google Cloud**: Compute Engine with GPU
- **Azure**: NV6 VM series

### 2. Containerization (Docker)

Sample Dockerfile:

```dockerfile
FROM nvidia/cuda:12.1-base
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Security Considerations

1. **Twilio Credentials**:
   - Never commit `.env` to version control
   - Use environment variables in production

2. **Patient Data**:
   - Consider encrypting appointment files
   - Implement proper access controls

3. **API Endpoints**:
   - Add authentication for `/webhook`
   - Implement rate limiting
   

## Support

For issues, please open a GitHub ticket or contact the maintainers.
