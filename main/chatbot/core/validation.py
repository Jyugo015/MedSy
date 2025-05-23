def validate_symptom(input_text: str) -> bool:
    return len(input_text.strip()) >= 3

def validate_yes_no(input_text: str) -> bool:
    return input_text.lower() in ["yes", "no"]

def validate_slot_selection(input_text: str, available_slots: list) -> bool:
    # Simple check if input matches any slot string (can be improved)
    return input_text.strip() in available_slots

def validate_name(input_text: str) -> bool:
    return len(input_text.strip()) >= 2
