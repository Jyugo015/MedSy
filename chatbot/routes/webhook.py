from flask import Blueprint, request
from twilio.rest import Client
from core.llm import llm_reply
from core.state_manager import get_state, reset_state
from core.booking import get_slots_for_department, save_appointment
from core.validation import validate_symptom, validate_yes_no, validate_slot_selection, validate_name
import re

webhook = Blueprint("webhook", __name__)

def phrase_in_text(phrase, text):
    phrase_tokens = phrase.split()
    text_tokens = text.split()
    for i in range(len(text_tokens) - len(phrase_tokens) + 1):
        if text_tokens[i:i+len(phrase_tokens)] == phrase_tokens:
            return True
    return False

# Initialize Twilio Client with environment vars or config
TWILIO_ACCOUNT_SID = "YOUR_ID"
TWILIO_AUTH_TOKEN = "YOUR_TOKEN"
TWILIO_PHONE_NUMBER = "whatsapp:+14155238886"
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

@webhook.route("/webhook", methods=["POST"])
def webhook_handler():
    try:
        user_input = request.values.get("Body", "").strip()
        user_id = request.values.get("From", "")

        state = get_state(user_id)
        step = state["step"]
        data = state["data"]

        if user_input.lower() == "restart":
            reset_state(user_id)
            reply = "Restarted. Hi! What symptoms are you experiencing?"
            send_whatsapp_message(user_id, reply)
            return "OK", 200

        # Handle conversation based on step
        reply = generate_response(user_id, user_input, step, data)
        send_whatsapp_message(user_id, reply)
        return "OK", 200
    except Exception as e:
        print("Error:", e)
        return "Internal Server Error", 500

def send_whatsapp_message(to, body):
    client.messages.create(
        body=body,
        from_=TWILIO_PHONE_NUMBER,
        to=to
    )

def generate_response(user_id, user_input, step, data):
    # Example with validation and slot retrieval
    if step == 0:
        get_state(user_id)["step"] = 1
        return "Hi! I'm your appointment assistant 🤖. What symptoms are you experiencing? 😷"

    elif step == 1:
        if not validate_symptom(user_input):
            return "Sorry, I didn't catch that. Could you describe your symptom again?"
        data["symptom"] = user_input
        department_map = {
            "headache": "Neurology",
            "fever": "General Medicine",
            "abdominal pain": "Gastroenterology",
            "cough": "Pulmonology",
            "flu": "General Medicine",
            "chest pain": "Cardiology",
            "skin rash": "Dermatology",
            "eye pain": "Ophthalmology",
            "toothache": "Dentistry",
            "back pain": "Orthopedics",
        }

        symptom_lower = user_input.lower()
        symptom_clean = re.sub(r'[^\w\s]', '', symptom_lower)
        department = "General Medicine"  # default
        earliest_index = len(symptom_clean) + 1
        matched_department = None

        for key, val in department_map.items():
            if phrase_in_text(key, symptom_clean):
                index = symptom_clean.find(key)
                if index != -1 and index < earliest_index:
                    earliest_index = index
                    matched_department = val

        if matched_department:
            department = matched_department

        data["department"] = department
        get_state(user_id)["step"] = 2

        prompt = (
                f"You are a polite medical assistant in Malaysia.\n"
                "Always answer according to Malaysian medical guidelines and common diseases in Malaysia.\n"
                f"A patient reports: '{user_input}'. You know the best department is {department}.\n"
                "Reply the user using I or We, not they.\n"
                "Politely suggest the department and ask if they would like to schedule an appointment.\n"
                "Reply to the user short and simple.\n"
                "Assistant:"
            )
        return llm_reply(prompt)

    elif step == 2:
        if not validate_yes_no(user_input):
            return "Please reply with 'yes' if you'd like to schedule, or 'no' if not."
        if user_input.lower() == "no":
            reset_state(user_id)
            return "No problem. Let me know if you need anything else."

        # yes branch
        slots = get_slots_for_department(data["department"])
        if not slots:
            return f"Sorry, there are currently no available slots for {data['department']}."

        slots_text = "\n".join(f"- {slot}" for slot in slots)
        get_state(user_id)["step"] = 3
        return f"Available slots for {data['department']}:\n{slots_text}\nPlease pick one."

    elif step == 3:
        slots = get_slots_for_department(data["department"])
        if not validate_slot_selection(user_input, slots):
            return "Please choose a valid slot from the available options."
        data["datetime"] = user_input
        get_state(user_id)["step"] = 4
        return "Great! Please provide your full name to confirm the booking."

    elif step == 4:
        if not validate_name(user_input):
            return "Please provide your full name."
        data["name"] = user_input
        save_appointment(data["name"], data["symptom"], data["department"], data["datetime"])
        get_state(user_id)["step"] = 5

        prompt = (
            f"You are a clinic assistant confirming a booking.\n"
            f"Patient: {data['name']}, symptom: {data['symptom']}, department: {data['department']}, appointment: {data['datetime']}.\n"
            "Write a short, friendly confirmation message.\n"
            "Assistant:"
        )
        return llm_reply(prompt)

    else:
        reset_state(user_id)
        return "Your booking is confirmed! 🎉 Type 'restart' if you want to make a new one."
