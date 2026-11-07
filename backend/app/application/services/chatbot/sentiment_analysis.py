"""Advanced sentiment analysis service for chatbot queries."""

import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)


class SentimentAnalysisService:
    """Service for analyzing sentiment in chatbot queries."""
    
    def __init__(self, use_advanced: bool = False):
        """
        Initialize sentiment analysis service.
        
        Args:
            use_advanced: If True, will use advanced analysis (can be extended with NLP libraries)
        """
        self.use_advanced = use_advanced
        
        # Turkish sentiment lexicons (can be expanded)
        self.positive_words = {
            "teşekkür", "harika", "güzel", "mükemmel", "iyi", "süper", "bravo", "elbette",
            "çok iyi", "hoş", "mutlu", "memnun", "beğendim", "takdir", "kutlar",
            "başarılı", "olumlu", "güzel gün", "iyi günler", "merhaba", "selam"
        }
        
        self.negative_words = {
            "kötü", "sorun", "hata", "yanlış", "memnun değil", "şikayet", "beğenmedim",
            "kızgın", "üzgün", "rahatsız", "endişe", "korku", "terrible", "berbat",
            "başarısız", "olumsuz", "yetersiz", "yetersiz", "istifra et", "yapamadım"
        }
        
        self.question_words = {
            "mi", "mı", "mu", "mü", "ne", "nasıl", "neden", "kaç", "kim", "nerede",
            "hangi", "kimin", "neden", "zaman", "miktar", "adet", "fark", "değer"
        }
        
        self.critical_words = {
            "acil", "acil durum", "kritik", "tehlike", "güvenlik", "sorun", "hata",
            "çökme", "bozulma", "felaket", "kriz", "önemli", "ciddi", "acele"
        }
    
    def analyze_sentiment(self, text: str) -> Literal["POSITIVE", "NEUTRAL", "QUESTION", "CRITICAL"]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment category: POSITIVE, NEUTRAL, QUESTION, CRITICAL
        """
        if not text:
            return "NEUTRAL"
        
        text_lower = text.lower().strip()
        
        # Check for critical indicators first (highest priority)
        critical_count = sum(1 for word in self.critical_words if word in text_lower)
        if critical_count >= 1:
            return "CRITICAL"
        
        # Check for question indicators
        if "?" in text or any(word in text_lower for word in self.question_words):
            return "QUESTION"
        
        # Count positive and negative words
        positive_count = sum(1 for word in self.positive_words if word in text_lower)
        negative_count = sum(1 for word in self.negative_words if word in text_lower)
        
        # Determine sentiment based on word counts
        if positive_count > negative_count and positive_count > 0:
            return "POSITIVE"
        elif negative_count > positive_count and negative_count > 0:
            return "CRITICAL"
        elif positive_count == negative_count and positive_count > 0:
            # Mixed sentiment - default to neutral
            return "NEUTRAL"
        
        return "NEUTRAL"
    
    def analyze_sentiment_with_score(
        self, 
        text: str
    ) -> dict[str, any]:
        """
        Analyze sentiment with detailed scoring.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment category and confidence score
        """
        if not text:
            return {
                "sentiment": "NEUTRAL",
                "confidence": 0.0,
                "positive_score": 0,
                "negative_score": 0,
                "question_score": 0,
                "critical_score": 0
            }
        
        text_lower = text.lower().strip()
        
        # Calculate scores
        positive_score = sum(1 for word in self.positive_words if word in text_lower)
        negative_score = sum(1 for word in self.negative_words if word in text_lower)
        question_score = 1 if "?" in text else sum(1 for word in self.question_words if word in text_lower)
        critical_score = sum(1 for word in self.critical_words if word in text_lower)
        
        # Determine sentiment
        sentiment = self.analyze_sentiment(text)
        
        # Calculate confidence (simple heuristic)
        total_score = positive_score + negative_score + question_score + critical_score
        confidence = min(total_score / 5.0, 1.0) if total_score > 0 else 0.0
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_score": positive_score,
            "negative_score": negative_score,
            "question_score": question_score,
            "critical_score": critical_score
        }
    
    def batch_analyze(self, texts: list[str]) -> list[dict[str, any]]:
        """
        Analyze sentiment for multiple texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment analysis results
        """
        return [self.analyze_sentiment_with_score(text) for text in texts]


# Global sentiment analysis service instance
sentiment_service = SentimentAnalysisService(use_advanced=False)


def analyze_sentiment(text: str) -> str:
    """
    Convenience function for sentiment analysis.
    
    Args:
        text: Text to analyze
        
    Returns:
        Sentiment category
    """
    return sentiment_service.analyze_sentiment(text)


def analyze_sentiment_with_score(text: str) -> dict[str, any]:
    """
    Convenience function for sentiment analysis with scoring.
    
    Args:
        text: Text to analyze
        
    Returns:
        Sentiment analysis result with scores
    """
    return sentiment_service.analyze_sentiment_with_score(text)
