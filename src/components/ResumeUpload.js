import React, { useState } from 'react';
import '../styles/ResumeUpload.css';

function ResumeUpload() {
  const [file, setFile] = useState(null);
  const [privacyAgreed, setPrivacyAgreed] = useState(false);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (file && privacyAgreed) {
      setIsLoading(true);
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://127.0.0.1:5000/process_resume', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Server response was not ok');
        }

        const data = await response.json();
        setResult(data);
      } catch (error) {
        console.error('Error:', error);
        setResult({ error: 'An error occurred while processing the resume.' });
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="resume-upload">
      <h2>Upload Your Resume</h2>
      <div className="privacy-notice">
        <h3>Privacy Policy</h3>
        <p>We prioritize your privacy. Your resume will be processed in-memory only, 
           will not be stored persistently, and will be deleted immediately after analysis. 
           We do not share your data with any third parties.</p>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="file-input">
          <input 
            type="file" 
            onChange={handleFileChange} 
            accept=".pdf,.docx" 
            required 
            id="file-upload" 
          />
          <label htmlFor="file-upload" className="file-label">
            {file ? file.name : 'Choose file'}
          </label>
        </div>
        <div className="privacy-agreement">
          <input 
            type="checkbox" 
            id="privacy-checkbox" 
            checked={privacyAgreed}
            onChange={(e) => setPrivacyAgreed(e.target.checked)}
            required 
          />
          <label htmlFor="privacy-checkbox">I have read and agree to the privacy policy</label>
        </div>
        <button type="submit" disabled={!file || !privacyAgreed || isLoading}>
          {isLoading ? 'Processing...' : 'Analyze Resume'}
        </button>
      </form>
      {result && (
        <div className="result">
          <h3>Analysis Result</h3>
          {result.error ? (
            <p className="error">{result.error}</p>
          ) : (
            <>
              <p>Score: {result.score}</p>
              <h4>Suggestions:</h4>
              <ul>
                {result.suggestions.map((suggestion, index) => (
                  <li key={index}>{suggestion}</li>
                ))}
              </ul>
              <h4>Matching Jobs:</h4>
              <ul>
                {result.matching_jobs.map((job, index) => (
                  <li key={index}>{job.title} at {job.company} - Match: {job.match_score}%</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default ResumeUpload;