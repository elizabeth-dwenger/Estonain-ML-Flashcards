# app.py - Flask backend

from flask import Flask, request, jsonify, send_file
import os
import requests
import json
import pandas as pd
import numpy as np
from flask_cors import CORS
from dotenv import load_dotenv
import tempfile
from datetime import datetime
import sqlite3
import logging

# ML recommendation model
from ml_model import FlashcardRecommender

# Initialize Flask app
app = Flask(__name__)
CORS(app)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize ML model
recommender = FlashcardRecommender()

# API endpoints configuration
TRANSLATION_API = os.getenv("TRANSLATION_API", "http://localhost:8000")
TTS_API = os.getenv("TTS_API", "http://localhost:8001")
DATABASE_PATH = os.getenv("DATABASE_PATH", "flashcards.db")

# Database setup
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY,
        estonian TEXT NOT NULL,
        translation TEXT,
        audio_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY,
        word_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        correct BOOLEAN NOT NULL,
        response_time REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (word_id) REFERENCES words (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Import words from Estonian word list
@app.route('/api/import-words', methods=['POST'])
def import_words():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        # Read words from file
        words = []
        for line in file:
            word = line.decode('utf-8').strip()
            if word:
                words.append(word)
        
        # Process words in batches
        batch_size = 100
        for i in range(0, len(words), batch_size):
            batch = words[i:i+batch_size]
            process_word_batch(batch)
            
        return jsonify({"message": f"Imported {len(words)} words successfully"}), 200
    
    except Exception as e:
        logger.error(f"Error importing words: {e}")
        return jsonify({"error": str(e)}), 500

def process_word_batch(words):
    """Process a batch of Estonian words"""
    conn = get_db_connection()
    
    for word in words:
        # Check if word already exists
        existing = conn.execute('SELECT id FROM words WHERE estonian = ?', (word,)).fetchone()
        if existing:
            continue
            
        # Add word to database
        cursor = conn.execute(
            'INSERT INTO words (estonian) VALUES (?)',
            (word,)
        )
        word_id = cursor.lastrowid
        
        # Queue translation and TTS tasks
        # In production, use Celery or similar task queue
        try:
            translation = translate_word(word)
            audio_path = generate_audio(word, word_id)
            
            conn.execute(
                'UPDATE words SET translation = ?, audio_path = ? WHERE id = ?',
                (translation, audio_path, word_id)
            )
        except Exception as e:
            logger.error(f"Error processing word {word}: {e}")
    
    conn.commit()
    conn.close()

def translate_word(estonian_word):
    """Translate Estonian word using the translation API"""
    try:
        payload = {
            "text": estonian_word,
            "src": "et",
            "tgt": "en",
            "domain": "auto",
            "application": "flashcard-app"
        }
        
        headers = {
            "x-api-key": "public",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{TRANSLATION_API}/translate",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("result", "")
        else:
            logger.error(f"Translation API error: {response.text}")
            return ""
    
    except Exception as e:
        logger.error(f"Translation request error: {e}")
        return ""

def generate_audio(estonian_word, word_id):
    """Generate audio using the TTS API"""
    try:
        payload = {
            "text": estonian_word,
            "speaker": "mari",  # Use Mari as default speaker
            "speed": 1.0
        }
        
        response = requests.post(
            f"{TTS_API}/synthesize",
            json=payload
        )
        
        if response.status_code == 200 and response.content:
            # Save audio file
            audio_dir = os.path.join(os.getcwd(), 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            
            audio_path = os.path.join(audio_dir, f"word_{word_id}.mp3")
            with open(audio_path, 'wb') as f:
                f.write(response.content)
                
            return audio_path
        else:
            logger.error(f"TTS API error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"TTS request error: {e}")
        return None

# Flashcard study endpoints
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    user_id = request.args.get('user_id', 1)  # Default user ID for demo
    count = int(request.args.get('count', 10))
    
    conn = get_db_connection()
    
    # Get study history for ML model
    study_sessions = conn.execute('''
        SELECT word_id as card_id, correct, response_time, timestamp
        FROM study_sessions
        WHERE user_id = ?
    ''', (user_id,)).fetchall()
    
    # Convert to dataframe
    if study_sessions:
        study_history = pd.DataFrame(study_sessions)
        
        # Convert timestamp string to datetime
        study_history['timestamp'] = pd.to_datetime(study_history['timestamp'])
        
        if len(study_history) >= 5:
            # Use ML model for recommendations
            try:
                # Train model if needed
                if not hasattr(recommender, 'model_trained') or not recommender.model_trained:
                    recommender.train(study_history)
                    recommender.model_trained = True
                    
                recommended_ids = recommender.get_recommendations(study_history, n=count)
                
                # Get recommended words
                placeholders = ','.join(['?'] * len(recommended_ids))
                words = conn.execute(f'''
                    SELECT id, estonian, translation, audio_path
                    FROM words
                    WHERE id IN ({placeholders})
                    AND translation IS NOT NULL
                ''', recommended_ids).fetchall()
            except Exception as e:
                logger.error(f"Error using ML model: {e}")
                # Fallback to random selection
                words = conn.execute('''
                    SELECT id, estonian, translation, audio_path
                    FROM words
                    WHERE translation IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (count,)).fetchall()
        else:
            # Not enough data for ML, return random words
            words = conn.execute('''
                SELECT id, estonian, translation, audio_path
                FROM words
                WHERE translation IS NOT NULL
                ORDER BY RANDOM()
                LIMIT ?
            ''', (count,)).fetchall()
    else:
        # No study history, return random words
        words = conn.execute('''
            SELECT id, estonian, translation, audio_path
            FROM words
            WHERE translation IS NOT NULL
            ORDER BY RANDOM()
            LIMIT ?
        ''', (count,)).fetchall()
    
    conn.close()
    
    return jsonify([dict(word) for word in words])

@app.route('/api/study-sessions', methods=['POST'])
def log_study_session():
    data = request.json
    
    if not data or 'word_id' not in data or 'correct' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO study_sessions (word_id, user_id, correct, response_time)
        VALUES (?, ?, ?, ?)
    ''', (
        data['word_id'],
        data.get('user_id', 1),  # Default user ID for demo
        data['correct'],
        data.get('response_time', 0)
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/api/audio/<int:word_id>', methods=['GET'])
def get_audio(word_id):
    conn = get_db_connection()
    word = conn.execute('SELECT audio_path FROM words WHERE id = ?', (word_id,)).fetchone()
    conn.close()
    
    if not word or not word['audio_path']:
        return jsonify({"error": "Audio not found"}), 404
    
    return send_file(word['audio_path'], mimetype='audio/mpeg')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
