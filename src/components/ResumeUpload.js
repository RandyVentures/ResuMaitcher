import React, { useState } from 'react';
import '../styles/ResumeUpload.css';

function ResumeUpload() {
  const [file, setFile] = useState(null);
  const [privacyAgreed, setPrivacyAgreed] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (file && privacyAgreed) {
      // Here you would handle the file upload and processing
      console.log('File uploaded:', file.name);
      // Implement API call to backend for processing
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
        <input type="file" onChange={handleFileChange} accept=".pdf,.docx" required />
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
        <button type="submit" disabled={!file || !privacyAgreed}>Analyze Resume</button>
      </form>
    </div>
  );
}

export default ResumeUpload;