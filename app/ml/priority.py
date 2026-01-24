"""
AI Priority Prediction Engine for AI-Powered To-Do List MVP

This module calculates dynamic priority scores for tasks based on:
1. Days until deadline (urgency)
2. User-assigned importance level
3. Historical postponement frequency
4. Historical completion speed vs estimates
5. Task age (how long it's been pending)

SCORING APPROACH:
- Rule-based weighted scoring (0-100 scale)
- Designed to be replaced with ML model later
- All decisions are logged and explainable

WEIGHTS (can be tuned):
- Deadline urgency: 30%
- Importance level: 25%
- Postponement history: 20%
- Estimation accuracy: 15%
- Task age: 10%

Higher scores = Higher priority = Should be done first
"""

from datetime import datetime
from sqlalchemy import func


def calculate_priority(task, user_id):
    """
    Calculate priority score for a task.
    
    Args:
        task: Task instance with all attributes
        user_id: User ID for historical analysis
    
    Returns:
        tuple: (score: float 0-100, label: str 'High'/'Medium'/'Low')
    
    AI Decision Log:
    - Each factor contributes to final score
    - Score is normalized to 0-100 range
    - Label thresholds: High >= 70, Medium >= 40, Low < 40
    """
    # Import here to avoid circular imports
    from ..models import TaskHistory, Task
    
    # Initialize component scores (each 0-100, will be weighted)
    urgency_score = 50  # Default: medium urgency
    importance_score = 50
    postponement_score = 50
    accuracy_score = 50
    age_score = 50
    
    # ==========================================================
    # FACTOR 1: DEADLINE URGENCY (30% weight)
    # Days until due date affects urgency exponentially
    # ==========================================================
    if task.due_date:
        days_until = task.days_until_due
        
        if days_until is None:
            urgency_score = 50
        elif days_until < 0:
            # Overdue: maximum urgency, scales with how overdue
            urgency_score = min(100, 100 + (days_until * 5))  # -1 day = 95, -2 days = 90, etc.
            urgency_score = max(urgency_score, 80)  # Minimum 80 for overdue
        elif days_until == 0:
            # Due today
            urgency_score = 95
        elif days_until == 1:
            # Due tomorrow
            urgency_score = 85
        elif days_until <= 3:
            # Due within 3 days
            urgency_score = 70
        elif days_until <= 7:
            # Due within a week
            urgency_score = 55
        else:
            # More than a week away - low urgency
            urgency_score = max(20, 50 - (days_until - 7) * 2)
    else:
        # No due date: moderate urgency based on importance
        urgency_score = 40
    
    # ==========================================================
    # FACTOR 2: USER IMPORTANCE LEVEL (25% weight)
    # Direct mapping from 1-5 scale to 0-100
    # ==========================================================
    # Importance is 1-5, map to 20-100
    importance_score = task.importance * 20
    
    # ==========================================================
    # FACTOR 3: POSTPONEMENT HISTORY (20% weight)
    # More postponements = higher priority (user avoiding task)
    # ==========================================================
    postponement_count = TaskHistory.query.filter_by(
        task_id=task.id,
        action='postponed'
    ).count()
    
    # Each postponement adds to priority
    # 0 postponements = 40 (neutral)
    # 1 postponement = 55
    # 2+ postponements = 70+
    postponement_score = min(100, 40 + (postponement_count * 15))
    
    # ==========================================================
    # FACTOR 4: ESTIMATION ACCURACY (15% weight)
    # If user typically underestimates, boost priority
    # ==========================================================
    # Get user's completed tasks with time data
    completed_with_times = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed',
        TaskHistory.actual_minutes.isnot(None)
    ).all()
    
    if completed_with_times:
        # Calculate average ratio of actual/estimated
        total_ratio = 0
        count = 0
        for history in completed_with_times:
            if history.task and history.task.estimated_minutes:
                ratio = history.actual_minutes / history.task.estimated_minutes
                total_ratio += ratio
                count += 1
        
        if count > 0:
            avg_ratio = total_ratio / count
            # If user typically takes longer than estimated (ratio > 1),
            # they may need more buffer time, so boost priority
            if avg_ratio > 1.5:
                accuracy_score = 75  # Significantly underestimates
            elif avg_ratio > 1.2:
                accuracy_score = 60  # Slightly underestimates
            elif avg_ratio < 0.8:
                accuracy_score = 35  # Overestimates (less urgent)
            else:
                accuracy_score = 50  # Accurate estimates
    
    # ==========================================================
    # FACTOR 5: TASK AGE (10% weight)
    # Older pending tasks should be addressed
    # ==========================================================
    task_age = task.task_age_days
    
    if task_age > 14:
        age_score = 80  # Very old task
    elif task_age > 7:
        age_score = 65  # Week old
    elif task_age > 3:
        age_score = 55  # Few days old
    else:
        age_score = 40  # Fresh task
    
    # ==========================================================
    # FINAL SCORE CALCULATION
    # Weighted combination of all factors
    # ==========================================================
    weights = {
        'urgency': 0.30,
        'importance': 0.25,
        'postponement': 0.20,
        'accuracy': 0.15,
        'age': 0.10
    }
    
    final_score = (
        urgency_score * weights['urgency'] +
        importance_score * weights['importance'] +
        postponement_score * weights['postponement'] +
        accuracy_score * weights['accuracy'] +
        age_score * weights['age']
    )
    
    # Ensure score is in valid range
    final_score = max(0, min(100, final_score))
    
    # Determine label
    if final_score >= 70:
        label = 'High'
    elif final_score >= 40:
        label = 'Medium'
    else:
        label = 'Low'
    
    return round(final_score, 1), label


def get_priority_explanation(task, user_id):
    """
    Generate human-readable explanation of priority calculation.
    Useful for viva demonstration and user transparency.
    
    Args:
        task: Task instance
        user_id: User ID
    
    Returns:
        dict: Breakdown of factors and their contributions
    """
    from ..models import TaskHistory, Task
    
    explanation = {
        'task_title': task.title,
        'final_score': task.priority_score,
        'label': task.priority_label,
        'factors': []
    }
    
    # Urgency explanation
    if task.due_date:
        days = task.days_until_due
        if days < 0:
            explanation['factors'].append(f"URGENT: Task is {abs(days)} day(s) overdue")
        elif days == 0:
            explanation['factors'].append("URGENT: Task is due today")
        elif days <= 3:
            explanation['factors'].append(f"Due soon: {days} day(s) remaining")
        else:
            explanation['factors'].append(f"Due in {days} days")
    else:
        explanation['factors'].append("No due date set")
    
    # Importance
    importance_labels = {1: 'Very Low', 2: 'Low', 3: 'Medium', 4: 'High', 5: 'Critical'}
    explanation['factors'].append(
        f"Importance: {importance_labels.get(task.importance, 'Medium')}"
    )
    
    # Postponements
    postponements = TaskHistory.query.filter_by(
        task_id=task.id, action='postponed'
    ).count()
    if postponements > 0:
        explanation['factors'].append(
            f"Postponed {postponements} time(s) - priority boosted"
        )
    
    # Age
    if task.task_age_days > 7:
        explanation['factors'].append(
            f"Task created {task.task_age_days} days ago - aging penalty applied"
        )
    
    return explanation
