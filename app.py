from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'aac', 'mp4', 'm4a'}

# Scam keywords list
scam_keywords = ["otp", "bank", "account", "password", "card", "transfer", "payment", "login", "refund", "loan", "income tax"]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return "Scam Detection Server is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    # Try to find an audio file
    audio = None
    for key in request.files:
        possible_file = request.files[key]
        if possible_file and possible_file.filename:
            audio = possible_file
            break

    if audio is None:
        return jsonify({'error': 'No audio file found'}), 400

    # Check file type 
    if not allowed_file(audio.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Generate unique ID for this job
    job_id = str(uuid.uuid4())
    
    # Save the file
    filename = secure_filename(f"{job_id}_{audio.filename}")
    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)
    audio.save(save_path)
    
    return jsonify({
        'status': 'success', 
        'job_id': job_id,
        'file_path': save_path,
        'message': 'File uploaded successfully'
    })

if __name__ == '__main__':
    # Ensure uploads directory exists
    os.makedirs('uploads', exist_ok=True)
    
    # Use a different port and enable debug
    app.run(host='0.0.0.0', port=10000, debug=True)
