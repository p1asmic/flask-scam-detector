from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
from werkzeug.utils import secure_filename
import logging

@app.route('/health')
def health_check():
    return 'OK', 200


# Set up basic logging configuration
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'aac'}

# Scam keywords list
scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

# Whisper model: Load once on startup
app.logger.info("🧠 Loading Whisper model...")
model = whisper.load_model("tiny")  # You can bump to "base" later
app.logger.info("✅ Whisper model loaded")

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Scam detection function
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
    return "Scam Detection Server is live! 🚨"

@app.route('/upload', methods=['POST'])
def upload_audio():
    app.logger.info("==> Incoming POST request to /upload")
    app.logger.info(f"Content-Type: {request.content_type}")
    app.logger.info(f"Form Keys: {list(request.form.keys())}")
    app.logger.info(f"Files Keys: {list(request.files.keys())}")

    # Try to find an audio file from the uploaded files
    audio = None
    for key in request.files:
        app.logger.info(f"Trying file field: {key}")
        possible_file = request.files[key]
        if possible_file.filename:
            audio = possible_file
            break

    if audio is None:
        app.logger.error("!! No audio file found in request")
        return jsonify({'error': 'No audio file found'}), 400

    # Check allowed file type
    if not allowed_file(audio.filename):
        app.logger.error("❌ File type not allowed")
        return jsonify({'error': 'File type not allowed. Only .aac accepted.'}), 400

    # Save the uploaded audio file
    filename = secure_filename(audio.filename)
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    audio.save(save_path)
    app.logger.info(f"✅ Saved file to: {save_path}")
    app.logger.info(f"📦 File size: {os.path.getsize(save_path)} bytes")

    # Run scam detection
    result = detect_scam_in_audio(save_path)
    app.logger.info(f"🧠 Scam detection result: {result}")

    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
