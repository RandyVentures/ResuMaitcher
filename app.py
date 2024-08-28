from flask import Flask, request, jsonify
from flask_cors import CORS
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import requests
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
import io
from pdfminer.high_level import extract_text
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
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


    sections = {
        'work_experience': [],
        'education': [],
        'skills': []
    }

    current_section = None
    for sent in doc.sents:
        text = sent.text.strip().lower()
        if 'work experience' in text or 'professional experience' in text:
            current_section = 'work_experience'
        elif 'education' in text:
            current_section = 'education'
        elif 'skills' in text or 'technical skills' in text:
            current_section = 'skills'
        elif current_section:
            sections[current_section].append(sent.text)
   
    return {
        "score": score,
        "entities": entities,
        "key_phrases": key_phrases,
        "important_terms": important_terms,
        "structured_info": sections
    }


def get_job_postings(keywords, location="", page=1):
    url = "https://jsearch.p.rapidapi.com/search"

    querystring = {
        "query": f"{' '.join(keywords)} {location}",
        "page": str(page),
        "num_pages": "5"
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
    job_titles = [phrase for phrase in analysis_result['key_phrases'] if 'engineer' in phrase.lower() or 'developer' in phrase.lower() or 'manager' in phrase.lower()]

    skills = set(analysis_result['structured_info']['skills'])

    keywords = list(skills) + job_titles * 2

    # Extract location if available
    #location = entities.get('GPE', '')  # GPE stands for Geopolitical Entity
    location = analysis_result['entities'].get('GPE', '')

    # Get job postings
    job_postings = get_job_postings(important_terms[:15], location)  # Use top 5 important terms
    
    #job_postings = get_job_postings(keywords[:15], location, page=1)  # Increase page number for more results

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

         # Add more matching criteria
        skill_match = len(set(analysis_result['structured_info']['skills']).intersection(set(job.get('job_highlights', {}).get('Qualifications', []))))
        experience_match = any(exp.lower() in job_description.lower() for exp in analysis_result['structured_info']['work_experience'])

        # Adjust similarity score based on additional criteria
        adjusted_score = similarity_score * 0.6 + (skill_match / 10) * 0.3 + (1 if experience_match else 0) * 0.1

        matching_jobs.append({
            "title": job_title,
            "company": company_name,
            "match_score": round(adjusted_score * 100, 2),
            "job_link": job.get('job_apply_link', ''),
            "skill_match": skill_match,
            "experience_match": experience_match
        })
    
    # Sort jobs by match score
    matching_jobs = sorted(matching_jobs, key=lambda x: x['match_score'], reverse=True)
    
    return matching_jobs[:10]  # Return top 10 matches


def generate_suggestions(analysis_result):
    suggestions = []

    # Check resume length
    word_count = len(analysis_result['important_terms'])
    if word_count < 300:
        suggestions.append("Your resume seems short. Consider adding more details about your experiences and skills.")
    elif word_count > 700:
        suggestions.append("Your resume is quite long. Consider condensing it to highlight your most relevant experiences.")

    # Check for key sections
    sections = analysis_result['structured_info']
    if not sections['work_experience']:
        suggestions.append("Consider adding a Work Experience section to your resume.")
    if not sections['education']:
        suggestions.append("An Education section would be beneficial to include in your resume.")
    if not sections['skills']:
        suggestions.append("Adding a Skills section can help highlight your key abilities.")

    # Check for action verbs
    action_verbs = ['achieved', 'improved', 'trained', 'managed', 'created', 'increased', 'decreased', 'developed']
    used_verbs = [word for word in analysis_result['important_terms'] if word in action_verbs]
    if len(used_verbs) < 3:
        suggestions.append("Try to use more action verbs to describe your achievements and responsibilities.")

    # Check for measurable achievements
    if not any(word in ' '.join(sections['work_experience']) for word in ['percent', '%', 'increased', 'decreased', 'reduced', 'improved']):
        suggestions.append("Include measurable achievements in your work experience to quantify your impact.")

    return suggestions

def extract_text_from_pdf(pdf_file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    
    for page in PDFPage.get_pages(pdf_file, caching=True, check_extractable=True):
        page_interpreter.process_page(page)
    
    text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    
    return text

@app.route('/process_resume', methods=['POST'])
def process_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        # Read the raw binary data
        filename = file.filename.lower()
        if filename.endswith('.docx'):
            # Process DOCX
            doc = Document(io.BytesIO(file.read()))
            resume_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        elif filename.endswith('.pdf'):
            # Process PDF
            resume_content = extract_text_from_pdf(io.BytesIO(file.read()))
        elif filename.endswith('.txt'):
            # Process plain text
            resume_content = file.read().decode('utf-8')
        else:
            return jsonify({"error": "Unsupported file format. Please upload a .docx, .pdf, or .txt file."}), 400

        #Extract text from the document
        #resume_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])


        # Process the resume
        analysis_result = analyze_resume(resume_content)

        matching_jobs = find_matching_jobs(analysis_result)

        suggestions = generate_suggestions(analysis_result)

        
        # suggestions = [
        #     "Consider adding more specific skills related to your field",
        #     f"Your resume mentions {len(analysis_result['entities'])} named entities. Consider adding more if relevant",
        #     "Try to incorporate more industry-specific keywords in your resume"
        # ]


        
        return jsonify({
            "score": analysis_result['score'],
            "suggestions": suggestions,
            "matching_jobs": matching_jobs,
            "analysis": {
                "important_terms": analysis_result['important_terms'],
                "key_phrases": analysis_result['key_phrases'][:5],  # Limiting to top 5 for brevity
                "entities": analysis_result['entities'],
                "structured_info": analysis_result['structured_info']
            }
        })

if __name__ == '__main__':
    app.run(debug=True)