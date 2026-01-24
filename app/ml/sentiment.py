"""
Sentiment Analysis Module for AI-Powered To-Do List MVP

This module analyzes text to determine user's emotional state:
- Task descriptions
- Daily reflections
- Any user-provided text

OUTPUT:
- Sentiment score: -1 (very negative) to +1 (very positive)
- Stress level: Low / Medium / High

USAGE:
- High stress → Use softer, encouraging reminder tones
- Low stress → Use direct, assertive reminders
- Affects notification language throughout the app

IMPLEMENTATION:
- Uses TextBlob for sentiment analysis
- Falls back to simple keyword matching if TextBlob unavailable
- Designed to be replaceable with more sophisticated NLP later
"""

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

# Stress-indicating keywords for fallback analysis
STRESS_KEYWORDS = {
    'high': [
        'urgent', 'asap', 'emergency', 'critical', 'deadline', 'overdue',
        'stressed', 'overwhelmed', 'anxious', 'worried', 'panic', 'help',
        'impossible', 'can\'t', 'won\'t', 'never', 'hate', 'terrible',
        'disaster', 'crisis', 'failing', 'behind', 'late', 'rush'
    ],
    'medium': [
        'busy', 'should', 'need to', 'have to', 'must', 'important',
        'concerned', 'difficult', 'challenging', 'tough', 'hard',
        'soon', 'quickly', 'hurry'
    ],
    'low': [
        'easy', 'simple', 'relaxed', 'calm', 'fine', 'good', 'great',
        'happy', 'excited', 'looking forward', 'enjoy', 'fun',
        'whenever', 'no rush', 'flexible'
    ]
}


def analyze_sentiment(text):
    """
    Analyze sentiment of provided text.
    
    Args:
        text: String to analyze (task description, reflection, etc.)
    
    Returns:
        tuple: (score: float -1 to +1, stress_level: str 'Low'/'Medium'/'High')
    
    AI Decision Log:
    - Uses TextBlob polarity score (-1 to +1)
    - Negative polarity correlates with higher stress
    - Additional keyword analysis for stress-specific language
    """
    if not text or not text.strip():
        return 0.0, 'Medium'
    
    text = text.lower().strip()
    
    if TEXTBLOB_AVAILABLE:
        return _analyze_with_textblob(text)
    else:
        return _analyze_with_keywords(text)


def _analyze_with_textblob(text):
    """
    Primary analysis using TextBlob NLP.
    
    TextBlob polarity:
    - -1.0: Very negative sentiment
    - 0.0: Neutral
    - +1.0: Very positive sentiment
    
    Stress mapping:
    - Negative sentiment often indicates stress
    - Combined with keyword detection for accuracy
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to +1
    
    # Check for stress keywords regardless of overall sentiment
    keyword_stress = _detect_stress_keywords(text)
    
    # Determine stress level
    # Combine polarity and keyword analysis
    if keyword_stress == 'high' or polarity < -0.3:
        stress_level = 'High'
    elif keyword_stress == 'low' and polarity > 0.2:
        stress_level = 'Low'
    elif polarity < -0.1 or keyword_stress == 'medium':
        stress_level = 'Medium'
    elif polarity > 0.3:
        stress_level = 'Low'
    else:
        stress_level = 'Medium'
    
    return round(polarity, 3), stress_level


def _analyze_with_keywords(text):
    """
    Fallback analysis using keyword matching.
    Used when TextBlob is not available.
    """
    keyword_stress = _detect_stress_keywords(text)
    
    # Map keyword stress to sentiment score
    if keyword_stress == 'high':
        score = -0.5
        stress_level = 'High'
    elif keyword_stress == 'low':
        score = 0.5
        stress_level = 'Low'
    else:
        score = 0.0
        stress_level = 'Medium'
    
    return score, stress_level


def _detect_stress_keywords(text):
    """
    Scan text for stress-indicating keywords.
    
    Returns: 'high', 'medium', 'low', or None
    """
    text_lower = text.lower()
    
    # Count keyword matches
    high_count = sum(1 for kw in STRESS_KEYWORDS['high'] if kw in text_lower)
    medium_count = sum(1 for kw in STRESS_KEYWORDS['medium'] if kw in text_lower)
    low_count = sum(1 for kw in STRESS_KEYWORDS['low'] if kw in text_lower)
    
    # Determine dominant stress level
    if high_count >= 2 or (high_count >= 1 and medium_count >= 2):
        return 'high'
    elif low_count >= 2 and high_count == 0:
        return 'low'
    elif medium_count >= 2 or high_count >= 1:
        return 'medium'
    elif low_count >= 1:
        return 'low'
    
    return None


def get_reminder_tone(user_id):
    """
    Determine appropriate reminder tone based on recent sentiment.
    
    Analyzes last 5 sentiment logs to determine current stress state.
    
    Args:
        user_id: User ID to analyze
    
    Returns:
        str: 'soft', 'neutral', or 'assertive'
    
    Tone mapping:
    - High stress → 'soft' (gentle, encouraging language)
    - Medium stress → 'neutral' (balanced, informative)
    - Low stress → 'assertive' (direct, action-oriented)
    """
    from ..models import SentimentLog
    
    # Get recent sentiment logs
    recent_logs = SentimentLog.query.filter_by(user_id=user_id).order_by(
        SentimentLog.timestamp.desc()
    ).limit(5).all()
    
    if not recent_logs:
        return 'neutral'
    
    # Calculate average stress
    stress_scores = {'Low': 1, 'Medium': 2, 'High': 3}
    total_stress = sum(stress_scores.get(log.stress_level, 2) for log in recent_logs)
    avg_stress = total_stress / len(recent_logs)
    
    if avg_stress >= 2.5:
        return 'soft'
    elif avg_stress <= 1.5:
        return 'assertive'
    else:
        return 'neutral'


def get_reminder_message(task, tone='neutral'):
    """
    Generate a reminder message with appropriate tone.
    
    Args:
        task: Task instance
        tone: 'soft', 'neutral', or 'assertive'
    
    Returns:
        str: Formatted reminder message
    """
    title = task.title
    
    if tone == 'soft':
        # Gentle, encouraging messages
        messages = [
            f"When you have a moment, '{title}' is waiting for you. No pressure! 🌱",
            f"Gentle reminder about '{title}'. Take your time and do what you can. 💙",
            f"'{title}' is on your list. Remember to take breaks when you need them! 🌟",
        ]
    elif tone == 'assertive':
        # Direct, action-oriented messages
        messages = [
            f"Time to tackle '{title}'! You've got this. 💪",
            f"'{title}' needs your attention. Let's get it done!",
            f"Action needed: '{title}' is waiting. Dive in!",
        ]
    else:
        # Balanced, informative messages
        messages = [
            f"Reminder: '{title}' is due soon.",
            f"Don't forget about '{title}'.",
            f"'{title}' is on your to-do list.",
        ]
    
    import random
    return random.choice(messages)


def analyze_daily_reflection(user_id, reflection_text):
    """
    Analyze a daily reflection entry and store sentiment.
    
    Args:
        user_id: User ID
        reflection_text: User's daily reflection text
    
    Returns:
        dict: Analysis results with score, stress level, and suggestions
    """
    from ..models import db, SentimentLog
    
    score, stress_level = analyze_sentiment(reflection_text)
    
    # Store the sentiment log
    log = SentimentLog(
        user_id=user_id,
        score=score,
        stress_level=stress_level,
        source_text=reflection_text[:500]  # Limit stored text
    )
    db.session.add(log)
    db.session.commit()
    
    # Generate suggestions based on sentiment
    suggestions = []
    if stress_level == 'High':
        suggestions = [
            "Consider taking a short break",
            "Focus on one task at a time",
            "It's okay to postpone non-urgent tasks",
            "Remember to breathe and stay hydrated"
        ]
    elif stress_level == 'Low':
        suggestions = [
            "Great energy! Consider tackling a challenging task",
            "Good time to work on important projects",
            "You're doing great - keep the momentum!"
        ]
    else:
        suggestions = [
            "Steady progress is key",
            "Balance your workload throughout the day"
        ]
    
    return {
        'score': score,
        'stress_level': stress_level,
        'suggestions': suggestions,
        'tone_recommendation': get_reminder_tone(user_id)
    }
