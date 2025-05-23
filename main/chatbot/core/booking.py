import json
from datetime import datetime
import os

SLOTS_PATH = "slots.json"
APPOINTMENTS_DIR = "appointments"

def get_slots_for_department(department: str):
    with open(SLOTS_PATH, "r") as f:
        slots_data = json.load(f)
    return slots_data.get(department, [])

def save_appointment(name: str, symptom: str, department: str, datetime_str: str):
    os.makedirs(APPOINTMENTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = name.replace(" ", "_")
    filename = f"{APPOINTMENTS_DIR}/{safe_name}_{timestamp}.txt"
    with open(filename, "w") as f:
        f.write(f"Name: {name}\n")
        f.write(f"Symptom: {symptom}\n")
        f.write(f"Department: {department}\n")
        f.write(f"Appointment Time: {datetime_str}\n")
