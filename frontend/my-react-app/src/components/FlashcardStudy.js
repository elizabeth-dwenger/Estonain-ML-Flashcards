// src/components/FlashcardStudy.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Flashcard from './Flashcard';

const API_BASE_URL = 'http://localhost:5000/api';

function FlashcardStudy() {
  const [cards, setCards] = useState([]);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [studyStats, setStudyStats] = useState({
    correct: 0,
    incorrect: 0
  });
  
  useEffect(() => {
    fetchRecommendations();
  }, []);
  
  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/recommendations?count=10`);
      setCards(response.data);
      setCurrentCardIndex(0);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleResponse = async (wordId, correct, responseTime) => {
    try {
      // Log study session
      await axios.post(`${API_BASE_URL}/study-sessions`, {
        word_id: wordId,
        correct,
        response_time: responseTime
      });
      
      // Update stats
      setStudyStats(prev => ({
        correct: prev.correct + (correct ? 1 : 0),
        incorrect: prev.incorrect + (correct ? 0 : 1)
      }));
      
      // Move to next card or fetch new cards
      if (currentCardIndex < cards.length - 1) {
        setCurrentCardIndex(currentCardIndex + 1);
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
    <div className="flashcard-study">
      <h2>Study Estonian Words</h2>
      
      <div className="study-stats">
        <span>Correct: {studyStats.correct}</span>
        <span>Incorrect: {studyStats.incorrect}</span>
      </div>
      
      <Flashcard 
        card={currentCard}
        onResponse={handleResponse}
      />
      
      <div className="progress">
        Card {currentCardIndex + 1} of {cards.length}
      </div>
    </div>
  );
}

export default FlashcardStudy;