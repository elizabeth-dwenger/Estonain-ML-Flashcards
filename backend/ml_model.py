import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlashcardRecommender:
    def __init__(self):
        # Pipeline with preprocessing and model
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(n_estimators=100))
        ])
        self.difficulty_predictor = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', RandomForestClassifier(n_estimators=50))
        ])
        self.model_trained = False
        
    def prepare_features(self, user_data):
        """
        Extract relevant features from user's study history
        """
        # Make sure we have data
        if len(user_data) == 0:
            return pd.DataFrame()
            
        # Check if dataframe is empty or missing required columns
        required_columns = ['card_id', 'correct', 'response_time', 'timestamp']
        if any(col not in user_data.columns for col in required_columns):
            logger.error(f"Missing required columns. Available columns: {user_data.columns}")
            raise ValueError("Missing required columns in user data")
            
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
            
        # Apply safely with error handling
        try:
            features['learning_trend'] = user_data.groupby('card_id').apply(calc_trend)
        except Exception as e:
            logger.error(f"Error calculating learning trend: {e}")
            features['learning_trend'] = 0
        
        # Forgetting curve estimation
        def estimate_forgetting_param(card_data):
            if len(card_data) < 3:
                return 0.3  # Default forgetting parameter
            # Simple exponential forgetting curve model
            correct_reviews = card_data[card_data['correct'] == 1]
            if len(correct_reviews) < 2:
                return 0.3
            
            try:
                intervals = np.diff(correct_reviews['timestamp'].values) / np.timedelta64(1, 'D')
                if len(intervals) == 0:
                    return 0.3
                    
                return np.mean(intervals) / 7  # Normalized to weekly basis
            except Exception as e:
                logger.error(f"Error estimating forgetting parameter: {e}")
                return 0.3
            
        # Apply safely with error handling
        try:
            features['forgetting_param'] = user_data.groupby('card_id').apply(estimate_forgetting_param)
        except Exception as e:
            logger.error(f"Error calculating forgetting parameters: {e}")
            features['forgetting_param'] = 0.3
        
        return features
        
    def train(self, user_data):
        """
        Train the model on user performance data
        """
        try:
            features = self.prepare_features(user_data)
            
            if len(features) == 0:
                logger.warning("No features to train on")
                return False
                
            # Target: Needs review (1) or not (0)
            # This is a simplified target - in practice you'd use a more nuanced approach
            target = (features['avg_accuracy'] < 0.8) | (features['days_since_last_review'] > 5)
            
            # Train model
            self.model.fit(features, target)
            
            # Train difficulty predictor
            difficulty_features = features[['avg_accuracy', 'avg_response_time']]
            difficulty_target = 1 - features['avg_accuracy']  # Higher value = more difficult
            
            self.difficulty_predictor.fit(difficulty_features, difficulty_target)
            self.model_trained = True
            
            logger.info(f"Model trained on {len(features)} examples")
            return True
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False
        
    def get_recommendations(self, user_data, n=10):
        """
        Get recommended flashcards to review
        """
        try:
            features = self.prepare_features(user_data)
            
            if len(features) == 0:
                # Return empty list if no features
                logger.warning("No features for recommendations")
                return []
                
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
            
            return recommended_ids.tolist()  # Convert to list for JSON serialization
        
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            # For now, just return an empty list if there's an error
            return []
    
    def update_model(self, user_data):
        """
        Update model after new study session
        """
        return self.train(user_data)
