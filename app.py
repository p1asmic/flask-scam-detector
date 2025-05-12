from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Load model ONCE (important!)
model = whisper.load_model("tiny")

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'aac'}

scam_keywords = [
    "otp", "bank", "account", "password", "card",
    "transfer", "payment", "login", "refund",
    "loan", "income tax"
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_scam_in_audio(audio_file_path):
    result = model.transcribe(audio_file_path)
    transcript = result['text']
    found = [word for word in scam_keywords if word.lower() in transcript.lower()]
    return {
        "status": "scam" if found else "safe",
        "keywords": found,
        "transcript": transcript
    }

@app.route('/')
def home():
    return "✅ Scam Detection Server is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    print("==> Incoming POST request to /upload")
    audio = next((f for f in request.files.values() if f.filename), None)

    if not audio:
        return jsonify({'error': 'No audio file found'}), 400

    if not allowed_file(audio.filename):
        return jsonify({'error': 'Only .aac files allowed'}), 400

    filename = secure_filename(audio.filename)
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    audio.save(save_path)

    result = detect_scam_in_audio(save_path)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
