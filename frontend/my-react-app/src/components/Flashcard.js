// src/components/Flashcard.js
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

function Flashcard({ card, onResponse }) {
  const [showTranslation, setShowTranslation] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const audioRef = useRef(null);
  
  useEffect(() => {
    // Reset card state when card changes
    setShowTranslation(false);
  }, [card]);
  
  const playAudio = async () => {
    try {
      if (audioRef.current) {
        audioRef.current.src = `${API_BASE_URL}/audio/${card.id}`;
        await audioRef.current.play();
      }
    } catch (error) {
      console.error('Error playing audio:', error);
    }
  };
  
  const handleShowTranslation = () => {
    setShowTranslation(true);
    setStartTime(Date.now());
    playAudio();
  };
  
  const handleResponse = (correct) => {
    const responseTime = (Date.now() - startTime) / 1000; // Convert to seconds
    onResponse(card.id, correct, responseTime);
  };
  
  return (
    <div className="flashcard">
      <div className="card-front">
        <h3>{card.estonian}</h3>
        <button className="audio-btn" onClick={playAudio}>
          🔊 Listen
        </button>
        <audio ref={audioRef} />
      </div>
      
      {showTranslation ? (
        <>
          <div className="card-back">
            <h3>{card.translation}</h3>
          </div>
          <div className="response-buttons">
            <button 
              className="incorrect-btn"
              onClick={() => handleResponse(false)}
            >
              Didn't Know
            </button>
            <button 
              className="correct-btn" 
              onClick={() => handleResponse(true)}
            >
              Knew It
            </button>
          </div>
        </>
      ) : (
        <button 
          className="show-answer-btn" 
          onClick={handleShowTranslation}
        >
          Show Translation
        </button>
      )}
    </div>
  );
}

export default Flashcard;