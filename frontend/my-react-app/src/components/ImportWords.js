// src/components/ImportWords.js
import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

function ImportWords() {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');
  
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };
  
  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setMessage('Please select a file');
      return;
    }
    
    setIsUploading(true);
    setMessage('Importing words, please wait...');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`${API_BASE_URL}/import-words`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setMessage(response.data.message);
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setIsUploading(false);
    }
  };
  
  return (
    <div className="import-section">
      <h2>Import Estonian Words</h2>
      <form onSubmit={handleUpload}>
        <div className="form-group">
          <label htmlFor="wordFile">Word List (text file):</label>
          <input
            type="file"
            id="wordFile"
            accept=".txt"
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </div>
        <button type="submit" disabled={isUploading}>
          {isUploading ? 'Uploading...' : 'Upload Words'}
        </button>
        {message && <p className="message">{message}</p>}
      </form>
    </div>
  );
}

export default ImportWords;