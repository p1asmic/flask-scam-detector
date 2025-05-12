from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
from werkzeug.utils import secure_filename
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('server_debug.log'),
                        logging.StreamHandler(sys.stdout)
                    ])

# Initialize Whisper model
model = whisper.load_model("tiny")  # Only load model when needed

app = Flask(__name__)
CORS(app)

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'aac', 'mp3', 'm4a'}

# Scam keywords list
scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Scam detection function
def detect_scam_in_audio(audio_file_path):
    logging.info(f"Starting scam detection on file: {audio_file_path}")
    try:
        result = model.transcribe(audio_file_path)
        transcript = result['text']
        logging.info(f"Transcription result: {transcript}")
        
        found = [word for word in scam_keywords if word.lower() in transcript.lower()]
        if found:
            return {"status": "scam", "keywords": found, "transcript": transcript}
        else:
            return {"status": "safe", "keywords": [], "transcript": transcript}
    except Exception as e:
        logging.error(f"Error in scam detection: {e}")
        return {"status": "error", "message": str(e)}

@app.route('/')
def home():
    return "Scam Detection Server is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    logging.info("==> Incoming POST request to /upload")
    logging.info(f"Content-Type: {request.content_type}")
    logging.info(f"Form Keys: {list(request.form.keys())}")
    logging.info(f"Files Keys: {list(request.files.keys())}")

    # Try to find an audio file from the uploaded files
    audio = None
    for key in request.files:
        logging.info(f"Trying file field: {key}")
        possible_file = request.files[key]
        if possible_file and possible_file.filename:
            audio = possible_file
            break

    if audio is None:
        logging.error("!! No audio file found in request")
        return jsonify({'error': 'No audio file found', 
                        'form_keys': list(request.form.keys()),
                        'files_keys': list(request.files.keys())}), 400

    # Check allowed file type
    if not allowed_file(audio.filename):
        logging.error(f"❌ File type not allowed: {audio.filename}")
        return jsonify({'error': 'File type not allowed. Only .aac, .mp4, .m4a accepted.'}), 400

    # Save the uploaded audio file
    filename = secure_filename(audio.filename)
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    
    try:
        audio.save(save_path)
        logging.info(f"✅ Saved file to: {save_path}")
        logging.info(f"📦 File size: {os.path.getsize(save_path)} bytes")
    except Exception as e:
        logging.error(f"Error saving file: {e}")
        return jsonify({'error': 'Failed to save audio file', 'details': str(e)}), 500

    # Run scam detection
    try:
        result = detect_scam_in_audio(save_path)
        logging.info(f"🧠 Scam detection result: {result}")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error in upload process: {e}")
        return jsonify({'error': 'Failed to process audio', 'details': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render sets this in prod
    app.run(host='0.0.0.0', port=port, debug=True)
