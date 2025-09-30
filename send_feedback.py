import requests
import json
import time

# List of feedback examples to automate
feedbacks = [
    {
        "feedback": "Accepted",
        "file": "../example_repo/main.py",
        "suggestion": "Remove unused import",
        "action": "accepted",
        "user": "shiva"
    },
    {
        "feedback": "Rejected",
        "file": "../example_repo/main.py",
        "suggestion": "Split long function",
        "action": "rejected",
        "user": "shiva"
    },
    {
        "feedback": "Edited",
        "file": "../example_repo/main.py",
        "suggestion": "Use logging instead of print",
        "action": "edited",
        "user": "shiva"
    }
]

url = "http://127.0.0.1:8000/feedback"
headers = {"Content-Type": "application/json"}

for fb in feedbacks:
    response = requests.post(url, data=json.dumps(fb), headers=headers)
    print(f"Sent feedback: {fb['suggestion']} | Status: {response.status_code}")
    time.sleep(0.5)  # Optional: avoid spamming the server
