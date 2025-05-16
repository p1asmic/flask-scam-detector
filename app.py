from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
import subprocess
from werkzeug.utils import secure_filename
import logging

# Set up basic logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
CORS(app)

@app.route('/health')
def health_check():
    return 'OK', 200

# Allow .3gp files
ALLOWED_EXTENSIONS = {'3gp'}

# Scam keyword list
scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

# Load Whisper once
app.logger.info("🧠 Loading Whisper model...")
model = whisper.load_model("tiny", device="cpu")
app.logger.info("✅ Whisper model loaded")

# File extension check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Scam detection logic
def detect_scam_in_audio(wav_file_path):
    result = model.transcribe(wav_file_path)
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

    # Get the uploaded file
    audio = None
    for key in request.files:
        app.logger.info(f"Trying file field: {key}")
        possible_file = request.files[key]
        if possible_file.filename:
            audio = possible_file
            break

    if audio is None:
        app.logger.error("❌ No audio file found")
        return jsonify({'error': 'No audio file found'}), 400

    if not allowed_file(audio.filename):
        app.logger.error("❌ File type not allowed")
        return jsonify({'error': 'File type not allowed. Only .3gp accepted.'}), 400

    # Save original .3gp file
    filename = secure_filename(audio.filename)
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    gp_path = os.path.join(save_dir, filename)
    audio.save(gp_path)
    app.logger.info(f"✅ Saved .3gp to: {gp_path}")

    # Convert to .wav using ffmpeg
    wav_path = os.path.join(save_dir, "converted.wav")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", gp_path, wav_path], check=True)
        app.logger.info(f"🔁 Converted to .wav at: {wav_path}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"FFmpeg conversion failed: {e}")
        return jsonify({'error': 'Audio conversion failed'}), 500

    # Transcribe and detect scam
    result = detect_scam_in_audio(wav_path)
    app.logger.info(f"🧠 Scam detection result: {result}")

    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
