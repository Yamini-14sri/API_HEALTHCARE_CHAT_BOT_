# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
# if not api_key:
#     print("❌ API Key not found")
#     exit()

# url = "https://openrouter.ai/api/v1/chat/completions"
# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json",
#     "HTTP-Referer": "http://localhost:5000",
#     "X-Title": "HealthBot"
# }
# payload = {
#     "model": "mistralai/mistral-7b-instruct",
#     "messages": [
#         {"role": "system", "content": "You are a helpful health assistant."},
#         {"role": "user", "content": "What should I do if I have a fever?"}
#     ]
# }

# try:
#     response = requests.post(url, headers=headers, json=payload)
#     print("Status Code:", response.status_code)
#     print("Response:", response.json())
# except Exception as e:
#     print("❌ API Error:", e)



# checking key

# import requests
# import os

# api_key = os.getenv("OPENROUTER_API_KEY")  # or paste your key here directly
# url = "https://openrouter.ai/api/v1/chat/completions"

# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json",
#     "HTTP-Referer": "http://localhost",
#     "X-Title": "HealthBot-Test"
# }

# payload = {
#     "model": "mistralai/mistral-7b-instruct",  # This is a free model
#     "messages": [
#         {"role": "user", "content": "Hello, are you working?"}
#     ]
# }

# response = requests.post(url, headers=headers, json=payload)

# print("Status Code:", response.status_code)
# print("Response:", response.json())


 # Should show your key (or 'None' if not loaded)
# import os
# import requests
# from dotenv import load_dotenv

# # Load .env file
# load_dotenv()

# # Get API key
# api_key = os.getenv("OPENROUTER_API_KEY")
# if not api_key:
#     raise ValueError("API Key not loaded. Check .env file!")

# # Show loaded key for debug (optional)
# print("Loaded API Key:", api_key)

# # Set headers
# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json"
# }

# # Payload
# data = {
#     "model": "mistralai/mistral-7b-instruct",
#     "messages": [
#         {"role": "user", "content": "What is fever?"}
#     ]
# }

# # Make request
# response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)

# # Show result
# print("Status Code:", response.status_code)
# print("Response:", response.json())



from langdetect import detect
from deep_translator import GoogleTranslator

text = "నీవు ఎలా ఉన్నావు?"  # Telugu text
language = detect(text)
print("Detected Language:", language)

translated = GoogleTranslator(source='auto', target='en').translate(text)
print("Translated Text:", translated)
