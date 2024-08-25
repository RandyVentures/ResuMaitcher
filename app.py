from flask import Flask, request, jsonify
from flask_cors import CORS
import io

app = Flask(__name__)
CORS(app)  # This allows your React app to make requests to this Flask app

def analyze_resume(resume_content):
    # Placeholder for AI model integration
    # For now, let's return a dummy score and suggestions
    score = 75
    suggestions = ["Add more keywords related to your industry", "Quantify your achievements"]
    return score, suggestions

def find_matching_jobs(resume_content):
    # Placeholder for job matching logic
    # For now, let's return dummy job matches
    return [
        {"title": "Software Developer", "company": "Tech Corp", "match_score": 85},
        {"title": "Data Analyst", "company": "Data Inc", "match_score": 70}
    ]

@app.route('/process_resume', methods=['POST'])
def process_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        # Read the raw binary data
        raw_data = file.read()
        
        # Try decoding with UTF-8 first
        try:
            resume_content = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            # If decoding with UTF-8 fails, try with another encoding (ISO-8859-1 as fallback)
            try:
                resume_content = raw_data.decode('iso-8859-1')
            except UnicodeDecodeError:
                return jsonify({"error": "Unable to decode file. Unsupported encoding."}), 400
        
        # Process the resume
        score, suggestions = analyze_resume(resume_content)
        matching_jobs = find_matching_jobs(resume_content)
        
        return jsonify({
            "score": score,
            "suggestions": suggestions,
            "matching_jobs": matching_jobs
        })

if __name__ == '__main__':
    app.run(debug=True)