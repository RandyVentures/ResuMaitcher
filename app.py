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
import re
from collections import Counter
import requests
from urllib.parse import quote, urlparse, parse_qs, urlencode
import json
import os

app = Flask(__name__)
CORS(app)  # This allows your React app to make requests to this Flask app

RAPID_API_KEY = 'eed202bb89mshd9b21b13318f667p11f8f8jsnff35708dbead'

nlp = spacy.load("en_core_web_sm")

def get_adzuna_job_postings(query, location="", page=1, results_per_page=50):
    app_id = "1fa58fd0"
    app_key = "c2179fdd4d0ea1822b1864cef6d5eaeb"
    
    base_url = "https://api.adzuna.com/v1/api/jobs"
    country = "us"
    
    # Prepare the query parameters
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json"
    }
    
    def make_request(where):
        # Update the 'where' parameter
        params["where"] = where
        
        # Construct the URL
        query_string = urlencode(params)
        url = f"{base_url}/{country}/search/{page}?{query_string}"
        
        print(f"Requesting URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching job postings from Adzuna: {e}")
            return None
    
    # First attempt with the provided location
    result = make_request(location)
    
    # If no results and location was provided, retry with "usa"
    if result and result.get("count", 0) == 0 and location:
        print("No results found. Retrying with location set to 'usa'...")
        result = make_request("usa")
    
    return result

def analyze_adzuna_jobs(adzuna_results, analysis_result):
    if not adzuna_results or 'results' not in adzuna_results:
        return []
    
    matching_jobs = []
    resume_text = " ".join(analysis_result['important_terms'] + 
                           analysis_result['structured_info']['skills'])
    
    for job in adzuna_results['results']:
        job_text = f"{job.get('title', '')} {job.get('description', '')}"
        
        # Calculate match score
        match_score = calculate_job_match_score(job_text, resume_text, analysis_result)
        
        #if match_score > 0.5:  # Only include jobs with a match score above 50%
        matching_jobs.append({
            "title": job.get('title', ''),
            "company": job.get('company', {}).get('display_name', ''),
            "match_score": round(match_score * 100, 2),
            "job_link": job.get('redirect_url', ''),
            "location": job.get('location', {}).get('display_name', ''),
            "salary_min": job.get('salary_min', 'Not specified'),
            "salary_max": job.get('salary_max', 'Not specified'),
            "description": job.get('description', '')[:200] + '...'  # First 200 characters of description
        })
    
    # Sort jobs by match score
    matching_jobs.sort(key=lambda x: x['match_score'], reverse=True)
    
    return matching_jobs[:10]  # Return top 10 matches


def calculate_job_match_score(job_text, resume_text, analysis_result):
    # Calculate TF-IDF similarity
    tfidf_similarity = calculate_similarity(resume_text, job_text)
    
    # Calculate skill match
    resume_skills = set(analysis_result['structured_info']['skills'])
    #job_skills = extract_skills(job_text)  # You'll need to implement this function
    #skill_match_ratio = len(resume_skills.intersection(job_skills)) / len(resume_skills) if resume_skills else 0
    
    # Calculate experience match
    experience_match = any(exp.lower() in job_text.lower() for exp in analysis_result['structured_info']['work_experience'])
    
    # Weighted score
    score = (tfidf_similarity * 0.5) + (0.2 if experience_match else 0)
    
    return score


def find_matching_jobs(analysis_result):
    job_titles = extract_job_titles(analysis_result)
    skills = extract_skills(analysis_result)
    
    # Combine job titles and skills for a more specific search
    search_terms = job_titles[:2]
    
    # Join search terms with OR for a broader search
    query = " ".join(f'"{term}"' for term in search_terms if term)
    
    location = clean_text(analysis_result['entities'].get('GPE', 'USA'))
    
    print("Extracted job titles:", job_titles)
    print("Generated search query:", query)

    adzuna_results = get_adzuna_job_postings(query, location)
    
    if adzuna_results:
        matching_jobs = analyze_adzuna_jobs(adzuna_results, analysis_result)
        return matching_jobs
    else:
        return []
    
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
        if 'work experience' in text or 'professional experience' in text or 'experience' in text:
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

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip().lower()


def extract_job_titles(analysis_result):
    common_job_titles = [
        'engineer', 'developer', 'manager', 'analyst', 'consultant', 'designer', 
        'coordinator', 'specialist', 'assistant', 'director', 'administrator', 
        'supervisor', 'technician', 'representative', 'associate', 'officer',
        'scientist', 'researcher', 'educator', 'teacher', 'professor',
        'accountant', 'architect', 'lawyer', 'physician', 'nurse',
        'marketing', 'sales', 'finance', 'human resources', 'operations',
        'project manager', 'product manager', 'data scientist', 'ux designer',
        'software engineer', 'web developer', 'systems administrator',
        'business analyst', 'financial analyst', 'research assistant',
        'executive assistant', 'customer service representative',
        'graphic designer', 'content writer', 'social media manager', 'internet sales',
        'senior software engineer', 'customer service representative', 'customer support',
        'principal engineer', 'engineer', 'salesman', 'tech lead', 'software developer', 'software engineering manager'
    ]

    full_text = clean_text(" ".join([
        " ".join(analysis_result['structured_info']['work_experience']),
        " ".join(analysis_result['structured_info']['education']),
        " ".join(analysis_result['key_phrases'])
    ]))

    potential_titles = []
    for title in common_job_titles:
        if title in full_text:
            potential_titles.append(title)
            # Look for variations with seniority levels
            for level in ['junior', 'senior', 'lead', 'principal']:
                if f"{level} {title}" in full_text:
                    potential_titles.append(f"{level} {title}")

    # Count occurrences and get the most common titles
    title_counts = Counter(potential_titles)
    most_common_titles = [title for title, count in title_counts.most_common(3)]

    return most_common_titles

def extract_skills(analysis_result):
    common_skills = [
        'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
        'html', 'css', 'react', 'angular', 'vue.js', 'node.js', 'express.js', 'django',
        'flask', 'spring', 'asp.net', 'ruby on rails',
        'mysql', 'postgresql', 'mongodb', 'oracle', 'sql server',
        'aws', 'azure', 'google cloud', 'docker', 'kubernetes', 'jenkins', 'git',
        'agile', 'scrum', 'jira', 'confluence', 'rest api', 'graphql',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
        'data analysis', 'data visualization', 'tableau', 'power bi',
        'linux', 'unix', 'windows server', 'networking', 'security'
    ]

    full_text = clean_text(" ".join([
        " ".join(analysis_result['structured_info']['skills']),
        " ".join(analysis_result['structured_info']['work_experience']),
        " ".join(analysis_result['key_phrases'])
    ]))

    extracted_skills = [skill for skill in common_skills if skill in full_text]
    return extracted_skills[:5]

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

        # Process the resume
        analysis_result = analyze_resume(resume_content)

        matching_jobs = find_matching_jobs(analysis_result)
        suggestions = generate_suggestions(analysis_result)

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