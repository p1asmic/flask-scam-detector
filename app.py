from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Scam Detection Server is live!"

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    audio = request.files['audio']
    
    # Save the uploaded audio file (optional, just for debugging)
    save_path = os.path.join("uploads", audio.filename)
    os.makedirs("uploads", exist_ok=True)
    audio.save(save_path)
    
    # Simulate detection - you'll replace this with ML model later
    transcript = "sample fake bank account scam message"
    if "account" in transcript.lower():
        return jsonify({"result": "Potential scam detected", "keyword": "account"})
    else:
        return jsonify({"result": "Clean", "keyword": None})

# This allows Render to bind to whatever port it assigns
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Render sets this
    app.run(host='0.0.0.0', port=port)
