import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class FlashcardRecommender:
    def __init__(self):
        # Pipeline with preprocessing and model
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(n_estimators=100))
        ])
        self.difficulty_predictor = None
        
    def prepare_features(self, user_data):
        """
        Extract relevant features from user's study history
        """
        features = pd.DataFrame()
        
        # Card-specific features
        features['avg_accuracy'] = user_data.groupby('card_id')['correct'].mean()
        features['review_count'] = user_data.groupby('card_id').size()
        features['avg_response_time'] = user_data.groupby('card_id')['response_time'].mean()
        
        # Recency features
        features['days_since_last_review'] = user_data.groupby('card_id')['timestamp'].max().apply(
            lambda x: (pd.Timestamp.now() - x).days)
        
        # Learning curve features
        # Calculate if performance is improving or declining
        def calc_trend(card_data):
            if len(card_data) < 3:
                return 0
            x = np.arange(len(card_data))
            y = card_data['correct'].values
            slope = np.polyfit(x, y, 1)[0]
            return slope
            
        features['learning_trend'] = user_data.groupby('card_id').apply(calc_trend)
        
        # Forgetting curve estimation
        def estimate_forgetting_param(card_data):
            if len(card_data) < 3:
                return 0.3  # Default forgetting parameter
            # Simple exponential forgetting curve model
            correct_reviews = card_data[card_data['correct'] == 1]
            if len(correct_reviews) < 2:
                return 0.3
            
            intervals = np.diff(correct_reviews['timestamp'].values) / np.timedelta64(1, 'D')
            if len(intervals) == 0:
                return 0.3
                
            return np.mean(intervals) / 7  # Normalized to weekly basis
            
        features['forgetting_param'] = user_data.groupby('card_id').apply(estimate_forgetting_param)
        
        return features
        
    def train(self, user_data):
        """
        Train the model on user performance data
        """
        features = self.prepare_features(user_data)
        
        # Target: Needs review (1) or not (0)
        # This is a simplified target - in practice you'd use a more nuanced approach
        target = (features['avg_accuracy'] < 0.8) | (features['days_since_last_review'] > 5)
        
        # Train model
        self.model.fit(features, target)
        
        # Train difficulty predictor
        difficulty_features = features[['avg_accuracy', 'avg_response_time']]
        difficulty_target = 1 - features['avg_accuracy']  # Higher value = more difficult
        self.difficulty_predictor = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', RandomForestClassifier(n_estimators=50))
        ])
        self.difficulty_predictor.fit(difficulty_features, difficulty_target)
        
    def get_recommendations(self, user_data, n=10):
        """
        Get recommended flashcards to review
        """
        features = self.prepare_features(user_data)
        
        # Predict priority score for review
        priority_scores = self.model.predict_proba(features)[:, 1]
        
        # Get card difficulty
        difficulty_features = features[['avg_accuracy', 'avg_response_time']]
        difficulties = self.difficulty_predictor.predict(difficulty_features)
        
        # Combine signals for final recommendation score
        recommendation_scores = 0.7 * priority_scores + 0.3 * difficulties
        
        # Return top n card IDs
        card_ids = features.index.values
        recommended_ids = card_ids[np.argsort(-recommendation_scores)[:n]]
        
        return recommended_ids
    
    def update_recommendations(self, user_id, study_session_data):
        """
        Update model after new study session
        """
        # In production, you might not retrain after every session
        # Instead, schedule periodic retraining or use online learning algorithms
        user_data = load_user_data(user_id)  # Function to load existing user data
        user_data = pd.concat([user_data, study_session_data])
        self.train(user_data)
        return self.get_recommendations(user_data)


# Example usage functions
def load_user_data(user_id):
    """Mock function to load user data"""
    # In a real application, this would fetch data from your database
    return pd.DataFrame()

def simulate_study_session():
    """Mock function to create study session data"""
    # This would be actual user interaction data in your application
    return pd.DataFrame({
        'card_id': [1, 2, 3, 4, 5],
        'correct': [1, 0, 1, 1, 0],
        'response_time': [1.2, 3.4, 0.9, 2.1, 4.5],
        'timestamp': pd.date_range(start='2024-03-01', periods=5)
    })
