from flask import Flask, request, jsonify
from flask_cors import CORS
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import requests
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__)
CORS(app)  # This allows your React app to make requests to this Flask app

RAPID_API_KEY = 'eed202bb89mshd9b21b13318f667p11f8f8jsnff35708dbead'


nlp = spacy.load("en_core_web_sm")


def analyze_resume(resume_content):
    doc = nlp(resume_content)
    
    # Extract entities
    entities = {ent.label_: ent.text for ent in doc.ents}
    
    # Extract key phrases (simplified)
    key_phrases = [chunk.text for chunk in doc.noun_chunks]
    
    # Use TF-IDF to get important terms
    vectorizer = TfidfVectorizer(max_features=100)
    tfidf_matrix = vectorizer.fit_transform([resume_content])
    feature_names = vectorizer.get_feature_names_out()
    
    # Convert to a list of important terms
    tfidf_scores = np.array(tfidf_matrix.sum(axis=0)).flatten()
    top_indices = tfidf_scores.argsort()[-10:][::-1]  # Get indices of top 10 terms
    important_terms = [feature_names[i] for i in top_indices]
    
    # Simplified scoring (just an example)
    score = min(100, (len(entities) + len(key_phrases) + len(important_terms)) * 2)
    
    return {
        "score": score,
        "entities": entities,
        "key_phrases": key_phrases,
        "important_terms": important_terms
    }



def get_job_postings(keywords, location="", page=1):
    url = "https://jsearch.p.rapidapi.com/search"
    print(keywords)
    print(location)
    querystring = {
        "query": f"{' '.join(keywords)} {location}",
        "page": str(page),
        "num_pages": "1"
    }
    
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Error fetching job postings: {response.status_code}")
        return []

def preprocess_text(text):
    # Convert to lowercase and tokenize
    tokens = nlp(text.lower())
    # Remove stop words and punctuation
    tokens = [token.text for token in tokens if not token.is_stop and not token.is_punct]
    return " ".join(tokens)

def calculate_similarity(resume_text, job_description):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]


def find_matching_jobs(analysis_result):
    important_terms = analysis_result['important_terms']
    entities = analysis_result['entities']
    
    # Extract location if available
    location = entities.get('GPE', '')  # GPE stands for Geopolitical Entity
    
    # Get job postings
    job_postings = get_job_postings(important_terms[:10], "")  # Use top 5 important terms
    
    # Prepare resume text for comparison
    resume_text = " ".join(important_terms + list(entities.values()))
    resume_text = preprocess_text(resume_text)
    
    matching_jobs = []
    for job in job_postings:
        job_description = job.get('job_description', '')
        job_title = job.get('job_title', '')
        company_name = job.get('employer_name', '')
        
        # Preprocess job description
        processed_job_description = preprocess_text(job_description)
        
        # Calculate similarity
        similarity_score = calculate_similarity(resume_text, processed_job_description)
        
        matching_jobs.append({
            "title": job_title,
            "company": company_name,
            "match_score": round(similarity_score * 100, 2),
            "job_link": job.get('job_apply_link', '')
        })
    
    # Sort jobs by match score
    matching_jobs = sorted(matching_jobs, key=lambda x: x['match_score'], reverse=True)
    
    return matching_jobs[:10]  # Return top 10 matches

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
        analysis_result = analyze_resume(resume_content)

        matching_jobs = find_matching_jobs(analysis_result)
        
        suggestions = [
            "Consider adding more specific skills related to your field",
            f"Your resume mentions {len(analysis_result['entities'])} named entities. Consider adding more if relevant",
            "Try to incorporate more industry-specific keywords in your resume"
        ]
        
        return jsonify({
            "score": analysis_result['score'],
            "suggestions": suggestions,
            "matching_jobs": matching_jobs,
            "analysis": {
                "important_terms": analysis_result['important_terms'],
                "key_phrases": analysis_result['key_phrases'][:5],  # Limiting to top 5 for brevity
                "entities": analysis_result['entities']
            }
        })

if __name__ == '__main__':
    app.run(debug=True)