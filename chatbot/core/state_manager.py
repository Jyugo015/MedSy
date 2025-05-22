user_state = {}

def get_state(user_id: str) -> dict:
    if user_id not in user_state:
        user_state[user_id] = {"step": 0, "data": {}}
    return user_state[user_id]

def reset_state(user_id: str):
    user_state[user_id] = {"step": 0, "data": {}}
