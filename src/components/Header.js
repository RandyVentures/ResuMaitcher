import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/Header.css';

function Header() {
  return (
    <header className="header">
      <div className="logo">
        <Link to="/">ResuMaitcher</Link>
      </div>
      <nav>
        <ul>
          <li><Link to="/">Home</Link></li>
          <li><Link to="/upload">Upload Resume</Link></li>
        </ul>
      </nav>
    </header>
  );
}

export default Header;