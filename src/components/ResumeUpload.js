import React, { useState } from 'react';
import '../styles/ResumeUpload.css';

function ResumeUpload() {
  const [file, setFile] = useState(null);
  const [privacyAgreed, setPrivacyAgreed] = useState(false);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fileType, setFileType] = useState(null);


  // const handleFileChange = (e) => {
  //   if (e.target.files[0]) {
  //     setFile(e.target.files[0]);
  //   }
  // };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    
    if (selectedFile) {
      const fileName = selectedFile.name.toLowerCase();
      if (fileName.endsWith('.docx')) {
        setFileType('DOCX');
      } else if (fileName.endsWith('.pdf')) {
        setFileType('PDF');
      } else if (fileName.endsWith('.txt')) {
        setFileType('TXT');
      } else {
        setFileType('Unknown');
      }
    } else {
      setFileType(null);
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
            <p>Overall Score: {result.score}</p>
            
            {<h4>Resume Analysis:</h4>}
            {<div className="analysis-section">
              <h5>Important Terms:</h5>
              <ul>
                {result.analysis.important_terms.map((term, index) => (
                  <li key={index}>{term}</li>
                ))}
              </ul>
              
              <h5>Key Phrases:</h5>
              <ul>
                {result.analysis.key_phrases.map((phrase, index) => (
                  <li key={index}>{phrase}</li>
                ))}
              </ul>
              
              <h5>Entities:</h5>
              <ul>
                {Object.entries(result.analysis.entities).map(([key, value], index) => (
                  <li key={index}>{key}: {value}</li>
                ))}
              </ul>
              
              <h5>Structured Information:</h5>
              <div className="structured-info">
                <h6>Work Experience:</h6>
                <ul>
                  {result.analysis.structured_info.work_experience.map((exp, index) => (
                    <li key={index}>{exp}</li>
                  ))}
                </ul>
                
                <h6>Education:</h6>
                <ul>
                  {result.analysis.structured_info.education.map((edu, index) => (
                    <li key={index}>{edu}</li>
                  ))}
                </ul>
                
                <h6>Skills:</h6>
                <ul>
                  {result.analysis.structured_info.skills.map((skill, index) => (
                    <li key={index}>{skill}</li>
                  ))}
                </ul>
              </div>
            </div>
       }
            <h4>Suggestions:</h4>
            <ul className="suggestions">
              {result.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
      
            <h4>Matching Jobs:</h4>
            <ul className="matching-jobs">
              {result.matching_jobs.map((job, index) => (
                <li key={index}>
                  <h5>{job.title} at {job.company}</h5>
                  <p>Match Score: {job.match_score}%</p>
                  <p>Skill Match: {job.skill_match} skills</p>
                  <p>Experience Match: {job.experience_match ? 'Yes' : 'No'}</p>
                  <a href={job.job_link} target="_blank" rel="noopener noreferrer">View Job</a>
                </li>
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