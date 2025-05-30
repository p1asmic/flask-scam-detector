from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
import subprocess
from werkzeug.utils import secure_filename
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max
CORS(app)

# Health route
@app.route('/health')
def health_check():
    return 'OK', 200

# Allowed audio formats
ALLOWED_EXTENSIONS = {'mp3'}

# Scam keywords to scan for
scam_keywords = [
    "otp", "bank", "account", "password", "card",
    "transfer", "payment", "login", "refund",
    "loan", "income tax"
]

# Load Whisper model once
app.logger.info("🧠 Loading Whisper model...")
model = whisper.load_model("tiny", device="cpu")
app.logger.info("✅ Whisper model loaded")

# File extension checker
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Scam keyword matcher
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

    audio = None

    # 1️⃣ Try request.files first (normal upload)
    for key in request.files:
        possible_file = request.files[key]
        if possible_file.filename:
            audio = possible_file
            break

    # 2️⃣ Try request.form fallback
    if not audio and 'file' in request.form:
        from io import BytesIO
        from base64 import b64decode
        try:
            audio_data = b64decode(request.form['file'])
            audio = BytesIO(audio_data)
            audio.filename = "uploaded.mp3"
        except Exception as e:
            app.logger.error(f"❌ Failed to decode base64: {e}")

    # 3️⃣ Try raw request.data (as last resort)
    if not audio and request.data:
        try:
            audio = BytesIO(request.data)
            audio.filename = "uploaded.mp3"
        except Exception as e:
            app.logger.error(f"❌ Failed to process raw data: {e}")

    if not audio:
        app.logger.error("❌ No audio file found in any method.")
        return jsonify({'error': 'No audio file found'}), 400

    # Check extension
    if not allowed_file(audio.filename):
        app.logger.error("❌ File type not allowed")
        return jsonify({'error': 'File type not allowed. Only .mp3 accepted.'}), 400

    # Save original audio
    filename = secure_filename(audio.filename)
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    gp_path = os.path.join(save_dir, filename)

    # If it's a stream, write it to disk
    if hasattr(audio, 'read'):
        with open(gp_path, 'wb') as f:
            f.write(audio.read())
    else:
        audio.save(gp_path)

    app.logger.info(f"✅ Saved audio to: {gp_path}")

    # Convert to .wav using ffmpeg
    wav_path = os.path.join(save_dir, "converted.wav")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", gp_path, wav_path], check=True)
        app.logger.info(f"🔁 Converted to .wav at: {wav_path}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"❌ FFmpeg conversion failed: {e}")
        return jsonify({'error': 'Audio conversion failed'}), 500

    # Scam detection
    result = detect_scam_in_audio(wav_path)
    app.logger.info(f"🧠 Scam detection result: {result}")

    return jsonify(result)

# Run server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
