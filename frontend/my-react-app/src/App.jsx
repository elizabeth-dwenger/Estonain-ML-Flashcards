import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:5000/api';

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Estonian Flashcards</h1>
      </header>
      <main>
        <ImportWords />
        <FlashcardStudy />
      </main>
    </div>
  );
}

// Word import component
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

// Flashcard study component
function FlashcardStudy() {
  const [cards, setCards] = useState([]);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [showTranslation, setShowTranslation] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [startTime, setStartTime] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioElement, setAudioElement] = useState(null);
  
  useEffect(() => {
    // Create audio element
    const audio = new Audio();
    setAudioElement(audio);
    
    // Fetch initial cards
    fetchRecommendations();
    
    // Cleanup audio element on unmount
    return () => {
      if (audio) {
        audio.pause();
        audio.src = '';
      }
    };
  }, []);
  
  useEffect(() => {
    // Update audio URL when currentCardIndex changes
    if (cards.length > 0 && currentCardIndex < cards.length) {
      setAudioUrl(`${API_BASE_URL}/audio/${cards[currentCardIndex].id}`);
    }
  }, [currentCardIndex, cards]);
  
  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/recommendations?count=10`);
      if (response.data && response.data.length > 0) {
        setCards(response.data);
        setCurrentCardIndex(0);
        setShowTranslation(false);
      } else {
        // Handle empty response
        setCards([]);
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const playAudio = async () => {
    if (!cards.length || !audioElement || !audioUrl) return;
    
    try {
      audioElement.src = audioUrl;
      await audioElement.load();
      await audioElement.play();
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };
  
  const handleShowTranslation = () => {
    setShowTranslation(true);
    setStartTime(Date.now());
    playAudio();
  };
  
  const handleResponse = async (correct) => {
    if (!startTime) return;
    
    const responseTime = (Date.now() - startTime) / 1000; // Convert to seconds
    
    try {
      // Log study session
      await axios.post(`${API_BASE_URL}/study-sessions`, {
        word_id: cards[currentCardIndex].id,
        correct,
        response_time: responseTime
      });
      
      // Move to next card or fetch new cards
      if (currentCardIndex < cards.length - 1) {
        setCurrentCardIndex(currentCardIndex + 1);
        setShowTranslation(false);
      } else {
        fetchRecommendations();
      }
    } catch (error) {
      console.error('Error logging study session:', error);
    }
  };
  
  if (isLoading) {
    return <div className="loading">Loading flashcards...</div>;
  }
  
  if (cards.length === 0) {
    return (
      <div className="no-cards">
        <p>No flashcards available. Please import some Estonian words first.</p>
      </div>
    );
  }
  
  const currentCard = cards[currentCardIndex];
  
  return (
    <div className="flashcard-container">
      <h2>Study Estonian Words</h2>
      
      <div className="flashcard">
        <div className="card-front">
          <h3>{currentCard.estonian}</h3>
          <button className="audio-btn" onClick={playAudio}>
            🔊 Listen
          </button>
        </div>
        
        {showTranslation ? (
          <>
            <div className="card-back">
              <h3>{currentCard.translation}</h3>
            </div>
            <div className="response-buttons">
              <button className="incorrect-btn" onClick={() => handleResponse(false)}>
                Didn't Know
              </button>
              <button className="correct-btn" onClick={() => handleResponse(true)}>
                Knew It
              </button>
            </div>
          </>
        ) : (
          <button className="show-btn" onClick={handleShowTranslation}>
            Show Translation
          </button>
        )}
      </div>
      
      <div className="progress">
        Card {currentCardIndex + 1} of {cards.length}
      </div>
    </div>
  );
}

export default App;