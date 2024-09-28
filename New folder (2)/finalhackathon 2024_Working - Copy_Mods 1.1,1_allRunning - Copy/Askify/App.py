from flask import Flask, render_template, request, jsonify
import requests
import json
import re

app = Flask(__name__)

# Function to generate chatbot response using Gemini API and extract bullet points
def generate_text(input_text):
    api_key = "AIzaSyBGEykAPgVXExWRmhROIYJIeisXudF9nfA"  # Replace with your actual API key
    endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'

    body = json.dumps({
        "contents": [{
            "parts": [{
                "text": input_text
            }]
        }]
    })

    try:
        response = requests.post(endpoint, headers={'Content-Type': 'application/json'}, data=body)
        response_data = response.json()
        full_response_text = response_data['candidates'][0]['content']['parts'][0]['text']

        # Remove asterisks from the response text
        full_response_text = re.sub(r'\*', '', full_response_text)

        # Regex to extract numbered points
        pattern = r'(\d+)\.\s(.*?)(?=\s*\d+\.|$)'
        matches = re.findall(pattern, full_response_text, re.DOTALL)

        # Sort the matches by the first capturing group (the number)
        sorted_points = sorted(matches, key=lambda x: int(x[0]))

        # Format the sorted points for display
        formatted_points = [f"{number}. {point.strip()}" for number, point in sorted_points]

        # Join the formatted points into a single string
        return "\n".join(formatted_points)
    except Exception as e:
        print("Error:", e)
        return "Error communicating with the Gemini API."

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    if user_message:
        # Call the Gemini API to get chatbot response and extract bullet points
        response_text = generate_text(user_message + " Give answer in numbered points and limit to 5 points and only give response for the Health and greeting related prompts ")
        return jsonify({'response': response_text})

    return jsonify({'response': "No message received"}), 400

if __name__ == '__main__':
    app.run(debug=True)
