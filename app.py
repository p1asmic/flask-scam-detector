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
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
CORS(app)

@app.route('/health')
def health_check():
    return 'OK', 200

ALLOWED_EXTENSIONS = {'mp3'}

scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

# Load Whisper once
app.logger.info("🧠 Loading Whisper model...")
model = whisper.load_model("tiny", device="cpu")
app.logger.info("✅ Whisper model loaded")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # Try regular file field
    for key in request.files:
        app.logger.info(f"Trying file field: {key}")
        possible_file = request.files[key]
        if possible_file.filename:
            audio = possible_file
            break

    # Fallback #1: App Inventor-style file in form
    if not audio and 'file' in request.form:
        app.logger.warning("⚠️ File found in form, saving manually...")
        audio_data = request.form['file']
        filename = "fallback_audio.mp3"
        save_dir = "uploads"
        os.makedirs(save_dir, exist_ok=True)
        gp_path = os.path.join(save_dir, filename)
        with open(gp_path, 'wb') as f:
            f.write(audio_data.encode())  # Optional: decode base64 if needed
        app.logger.info(f"✅ Saved fallback form audio to: {gp_path}")

    # Fallback #2: Raw data body
    elif not audio and request.data:
        app.logger.warning("⚠️ Using raw request.data as audio...")
        filename = "raw_upload.mp3"
        save_dir = "uploads"
        os.makedirs(save_dir, exist_ok=True)
        gp_path = os.path.join(save_dir, filename)
        with open(gp_path, 'wb') as f:
            f.write(request.data)
        app.logger.info(f"✅ Saved raw audio to: {gp_path}")

    # Regular upload flow
    elif audio:
        if not allowed_file(audio.filename):
            app.logger.error("❌ File type not allowed")
            return jsonify({'error': 'File type not allowed. Only .mp3 accepted.'}), 400

        filename = secure_filename(audio.filename)
        save_dir = "uploads"
        os.makedirs(save_dir, exist_ok=True)
        gp_path = os.path.join(save_dir, filename)
        audio.save(gp_path)
        app.logger.info(f"✅ Saved .mp3 to: {gp_path}")
    else:
        app.logger.error("❌ No audio file found at all")
        return jsonify({'error': 'No audio file found'}), 400

    # Convert to WAV
    wav_path = os.path.join("uploads", "converted.wav")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", gp_path, wav_path], check=True)
        app.logger.info(f"🔁 Converted to .wav at: {wav_path}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"FFmpeg conversion failed: {e}")
        return jsonify({'error': 'Audio conversion failed'}), 500

    # Transcribe + Detect
    result = detect_scam_in_audio(wav_path)
    app.logger.info(f"🧠 Scam detection result: {result}")
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
