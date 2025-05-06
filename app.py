from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Load Whisper model (use "tiny" for faster processing)
model = whisper.load_model("tiny")

# List of scam keywords
scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

# Function to detect scam in audio
def detect_scam_in_audio(audio_file_path):
    # Transcribe audio
    result = model.transcribe(audio_file_path)
    transcript = result['text']

    # Check for scam keywords
    found = [word for word in scam_keywords if word.lower() in transcript.lower()]

    if found:
        return {"status": "scam", "keywords": found, "transcript": transcript}
    else:
        return {"status": "safe", "keywords": [], "transcript": transcript}

@app.route('/')
def home():
    return "Scam Detection Server is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio = request.files['file']
    
    # Save the uploaded audio file
    save_path = os.path.join("uploads", secure_filename(audio.filename))
    os.makedirs("uploads", exist_ok=True)
    audio.save(save_path)
    
    # Perform scam detection
    result = detect_scam_in_audio(save_path)
    
    # Return the result in JSON format
    return jsonify(result)

# This allows Render to bind to whatever port it assigns
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render sets this
    app.run(host='0.0.0.0', port=port)
