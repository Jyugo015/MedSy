from flask import Flask, request
from twilio.rest import Client
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os
from datetime import datetime

app = Flask(__name__)

print(torch.__version__)          
print(torch.cuda.is_available())   
print(torch.cuda.get_device_name(0))  

# Twilio credentials
TWILIO_ACCOUNT_SID = 'YOUR_ID'
TWILIO_AUTH_TOKEN = 'YOUR_TOKEN'
TWILIO_PHONE_NUMBER = 'whatsapp:+14155238886'
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

today = datetime.today()

# --- LLM Setup ---
model_name = "mistralai/Mistral-7B-Instruct-v0.2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map={"": 0}, 
    torch_dtype=torch.float16,
    load_in_8bit=True
)
# --- In-memory chat state ---
user_state = {}

def llm_reply(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    output_ids = model.generate(
        **inputs, max_new_tokens=100,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )
    text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return text.split("Assistant:")[-1].strip()

# --- Define the conversation logic ---
def generate_response(user_id, user_input):
    if user_id not in user_state:
        user_state[user_id] = {"step": 0, "data": {}}

    state = user_state[user_id]
    step = state["step"]
    data = state["data"]
    user_input_lower = user_input.lower()

    if step == 0:
        state["step"] = 1
        return "Hi~ I'm your appointment assistant! What symptoms are you experiencing? 😷"

    elif step == 1:
        data["symptom"] = user_input
        symptom = user_input.lower()
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
        department = department_map.get(symptom, "General Medicine")
        data["department"] = department
        state["step"] = 2

        prompt = (
            "You are a polite and concise medical assistant.\n"
            f"A patient reports: '{symptom}'. You know the best department is {department}.\n"
            "Reply the user using I or We, not they\n"
            "Politely suggest the department and ask them would like to schedule a appointment\n"
            "Reply the user short and simple. \n"
            "Assistant:"
        )
        return llm_reply(prompt)

    elif step == 2:
        if "yes" in user_input_lower:
            state["step"] = 3
            prompt = (
                f"You are a clinic assistant confirming an appointment.\n"
                f"The user has symptoms: {data['symptom']}.\n"
                f"You recommended: {data['department']}.\n"
                f"You know today is {today}"
                f"Now user want to book an appointment, you need to give them some empty slot that they can book the appointment\n"
                f"Reply the user using I or We, not they\n"
                f"Simply generate few datetime (have specified date) after today for user to select for the booking\n"
                f"Ask them politely to select the datetime for appoint you given.\n"
                f"Assistant:"
            )
            return llm_reply(prompt)
            # return "Great! When would you like to come in for your appointment?"
        elif "no" in user_input_lower:
            state["step"] = 0
            return "No problem. Let me know if you need help with anything else."
        else:
            return "Please reply with 'yes' if you'd like to schedule, or 'no' if not."

    elif step == 3:
        data["datetime"] = user_input
        state["step"] = 4

        prompt = (
            f"You are a clinic assistant confirming an appointment.\n"
            f"The user has symptoms: {data['symptom']}.\n"
            f"You recommended: {data['department']}.\n"
            f"The user wants to come on: {data['datetime']}.\n"
            f"Reply the user using I or We, not they\n"
            f"Ask them politely to provide their full name to proceed with the booking.\n"
            f"Assistant:"
        )
        return llm_reply(prompt)

    elif step == 4:
        data["name"] = user_input
        state["step"] = 5

        os.makedirs("appointments", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = data['name'].replace(" ", "_")
        filename = f"appointments/{safe_name}_{timestamp}.txt"

        with open(filename, "w") as f:
            f.write(f"Name: {data['name']}\n")
            f.write(f"Symptom: {data['symptom']}\n")
            f.write(f"Department: {data['department']}\n")
            f.write(f"Appointment Time: {data['datetime']}\n")

        prompt = (
            f"You are a clinic assistant confirming a booking.\n"
            f"Patient name: {data['name']}, symptom: {data['symptom']}, "
            f"department: {data['department']}, appointment: {data['datetime']}.\n"
            f"Write a short, friendly confirmation message for the booking.\n"
            "Reply the user short and simple. \n"
            f"Assistant:"
        )
        return llm_reply(prompt)

    else:
        return "You've completed your booking! 🎉 Type 'restart' if you want to make a new one."



# --- Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        user_input = request.values.get("Body", "").strip()
        user_id = request.values.get("From", "")

        if user_input.lower() == "restart":
            user_state[user_id] = {"step": 0, "data": {}}
            reply = generate_response(user_id, user_input)
        else:
            reply = generate_response(user_id, user_input)

        client.messages.create(
            body=reply,
            from_=TWILIO_PHONE_NUMBER,
            to=user_id
        )

        return "OK", 200
    except Exception as e:
        print("Error:", e)
        return "Internal Server Error", 500

def local_test():
    print("Local test mode (Enter 'exit' to quit)")
    user_id = "local_test_user"

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        if user_input.lower() == "restart":
            user_state[user_id] = {"step": 0, "data": {}}

        reply = generate_response(user_id, user_input)
        print("Assistant:", reply)

if __name__ == "__main__":
    import sys
    if "--local" in sys.argv:
        local_test()
    else:
        app.run(debug=True)
