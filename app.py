from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import whisper
import subprocess
from werkzeug.utils import secure_filename
import logging
from datetime import datetime

# Set up enhanced logging with timestamps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
# Increase max content length to 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
# Configure CORS properly
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["POST", "GET", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Allow MP3 files
ALLOWED_EXTENSIONS = {'mp3'}

# Enhanced scam keyword list
scam_keywords = [
    "otp", "bank", "account", "password", "card", "transfer", 
    "payment", "login", "refund", "loan", "income tax",
    "urgent", "cryptocurrency", "bitcoin", "wallet", "verify",
    "suspicious", "activity", "security", "compromise"
]

# Load Whisper model with error handling
try:
    app.logger.info("🧠 Loading Whisper model...")
    model = whisper.load_model("tiny", device="cpu")
    app.logger.info("✅ Whisper model loaded successfully")
except Exception as e:
    app.logger.error(f"❌ Failed to load Whisper model: {str(e)}")
    raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_scam_in_audio(wav_file_path):
    try:
        result = model.transcribe(wav_file_path)
        transcript = result['text'].lower()
        found_keywords = [word for word in scam_keywords if word.lower() in transcript]
        
        # Calculate confidence score based on number of keywords found
        confidence_score = min(len(found_keywords) * 0.2, 1.0)
        
        return {
            "status": "scam" if found_keywords else "safe",
            "confidence": round(confidence_score, 2),
            "keywords": found_keywords,
            "transcript": result['text'],
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        app.logger.error(f"Error in scam detection: {str(e)}")
        raise

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "whisper_model": "tiny"
    }), 200

@app.route('/')
def home():
    return jsonify({
        "service": "Audio Scam Detection API",
        "status": "active",
        "endpoints": {
            "/upload": "POST - Upload audio for scam detection",
            "/health": "GET - Service health check"
        }
    })

@app.route('/upload', methods=['POST'])
def upload_audio():
    app.logger.info("==> Incoming POST request to /upload")
    app.logger.debug(f"Request Headers: {dict(request.headers)}")
    app.logger.debug(f"Files in request: {list(request.files.keys())}")
    
    try:
        # Check all possible file field names that MIT App Inventor might use
        audio = None
        for key in ['file', 'audio', 'responseContent', 'FileUpload']:
            if key in request.files:
                possible_file = request.files[key]
                if possible_file.filename:
                    audio = possible_file
                    app.logger.info(f"Found file in field: {key}")
                    break

        if audio is None:
            app.logger.error("❌ No audio file found in request")
            return jsonify({
                'error': 'No audio file found',
                'message': 'Please ensure you are sending an audio file',
                'available_fields': list(request.files.keys())
            }), 400

        if not allowed_file(audio.filename):
            app.logger.error(f"❌ Invalid file type: {audio.filename}")
            return jsonify({
                'error': 'Invalid file type',
                'message': 'Only MP3 files are accepted',
                'allowed_extensions': list(ALLOWED_EXTENSIONS)
            }), 400

        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = secure_filename(f"{timestamp}_{audio.filename}")
        save_dir = "uploads"
        os.makedirs(save_dir, exist_ok=True)
        
        # Save original file
        audio_path = os.path.join(save_dir, filename)
        audio.save(audio_path)
        app.logger.info(f"✅ Saved audio file to: {audio_path}")

        # Process audio and detect scam
        result = detect_scam_in_audio(audio_path)
        
        # Clean up files
        try:
            os.remove(audio_path)
            app.logger.info(f"🧹 Cleaned up temporary file: {audio_path}")
        except Exception as e:
            app.logger.warning(f"Warning: Could not delete temporary file: {str(e)}")

        return jsonify({
            "success": True,
            "data": result,
            "message": "Audio analysis completed successfully"
        })

    except Exception as e:
        app.logger.error(f"❌ Error processing upload: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
