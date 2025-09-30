import math

class Calculator:
    def __init__(self):
        self.memory = []

    def add(self, a, b):
        result = a + b
        self.memory.append(result)
        return result

    def multiply(self, a, b):
        result = a * b
        self.memory.append(result)
        return result

    def sqrt(self, x):
        if x < 0:
            print("Cannot take sqrt of negative number")
            return None
        result = math.sqrt(x)
        self.memory.append(result)
        return result

    def clear(self):
        self.memory = []

def main():
import requests
import json

def test_gemini_suggest(file_path):
    url = "http://127.0.0.1:8000/suggest"
    payload = {"path": file_path}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print("Status Code:", response.status_code)
        print("Response:")
        print(response.json())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    # Test Gemini refactor suggestions on this file
    test_gemini_suggest("example_repo/main.py")
    # You can also test other files by changing the path
    # test_gemini_suggest("example_repo/other_file.py")

if __name__ == "__main__":
    main()