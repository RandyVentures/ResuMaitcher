import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/LandingPage.css';

function LandingPage() {
  return (
    <div className="landing-page">
      <section className="hero">
        <h1>Welcome to ResuMaitcher</h1>
        <p>Analyze your resume and find matching job positions with AI</p>
        <Link to="/upload" className="cta-button">Get Started</Link>
      </section>
      
      <section className="features">
        <h2>Our Features</h2>
        <div className="feature-grid">
          <div className="feature">
            <h3>AI-powered Analysis</h3>
            <p>Get instant feedback on your resume quality</p>
          </div>
          <div className="feature">
            <h3>Job Matching</h3>
            <p>Find positions that fit your skills and experience</p>
          </div>
          <div className="feature">
            <h3>Privacy First</h3>
            <p>Your data is processed securely and never stored</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default LandingPage;