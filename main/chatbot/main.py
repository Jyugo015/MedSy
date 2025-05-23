from flask import Flask
from routes.webhook import webhook  # Adjust if your generate_response is elsewhere
from core.state_manager import user_state  # Or wherever your state is
import sys

app = Flask(__name__)
app.register_blueprint(webhook)

def local_test():
    print("=== Local test mode. Type 'exit' to quit. ===")
    user_id = "local_test_user"

    # Reset user state for testing
    user_state[user_id] = {"step": 0, "data": {}}

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break
        # Import or call your generate_response logic here
        from routes.webhook import generate_response  # Or core.conversation, wherever defined

        reply = generate_response(user_id, user_input, 
                                  user_state[user_id]["step"], 
                                  user_state[user_id]["data"])
        print("Assistant:", reply)

if __name__ == "__main__":
    if "--local" in sys.argv:
        local_test()
    else:
        app.run(debug=True)
