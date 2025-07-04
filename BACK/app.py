import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = "asst_ZR2gfUCMpx6wen6ZRvAEFJlC"
OPENAI_API_URL = "https://api.openai.com/v1/threads"

app = Flask(__name__)
CORS(app)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")
    thread_id = data.get("thread_id")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2"
    }

    # Step 1: Create a thread if not provided
    if not thread_id:
        thread_res = requests.post(OPENAI_API_URL, headers=headers, json={})
        if thread_res.status_code != 200:
            return jsonify({"error": "Failed to create thread", "details": thread_res.text}), 500
        thread_id = thread_res.json()["id"]

    # Step 2: Add user message to thread
    msg_res = requests.post(f"{OPENAI_API_URL}/{thread_id}/messages", headers=headers, json={
        "role": "user",
        "content": user_message
    })
    if msg_res.status_code != 200:
        return jsonify({"error": "Failed to add message", "details": msg_res.text}), 500

    # Step 3: Run the assistant
    run_res = requests.post(f"{OPENAI_API_URL}/{thread_id}/runs", headers=headers, json={
        "assistant_id": OPENAI_ASSISTANT_ID
    })
    if run_res.status_code != 200:
        return jsonify({"error": "Failed to run assistant", "details": run_res.text}), 500

    run_data = run_res.json()
    run_id = run_data["id"]

    # Step 4: Poll for completion
    import time
    status = run_data["status"]
    attempts = 0
    while status != "completed" and attempts < 30:
        time.sleep(1)
        poll_res = requests.get(f"{OPENAI_API_URL}/{thread_id}/runs/{run_id}", headers=headers)
        if poll_res.status_code != 200:
            return jsonify({"error": "Failed to poll run", "details": poll_res.text}), 500
        poll_data = poll_res.json()
        status = poll_data["status"]
        attempts += 1

    # Step 5: Get the latest assistant message
    msgs_res = requests.get(f"{OPENAI_API_URL}/{thread_id}/messages?limit=10", headers=headers)
    if msgs_res.status_code != 200:
        return jsonify({"error": "Failed to get messages", "details": msgs_res.text}), 500
    msgs_data = msgs_res.json()
    assistant_msg = next((m for m in reversed(msgs_data["data"]) if m["role"] == "assistant"), None)
    reply = assistant_msg["content"][0]["text"]["value"] if assistant_msg else "No response from Swallow."
    return jsonify({"reply": reply, "thread_id": thread_id})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
