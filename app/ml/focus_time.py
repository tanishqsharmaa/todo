

from datetime import datetime, timedelta
from collections import defaultdict

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def get_productive_hours(user_id):
    """
    Analyze user's task completion patterns to find most productive hours.
    
    Args:
        user_id: User ID to analyze
    
    Returns:
        list: Top productive time windows with details
              [{'start_hour': 9, 'end_hour': 11, 'productivity_score': 85, ...}, ...]
    
    AI Decision Log:
    - Analyzes completion timestamps to find peak hours
    - Considers both quantity and quality (actual vs estimated time)
    - Returns top 2 windows by default
    """
    from ..models import TaskHistory, Task, FocusSession
    
    # Get completed tasks with timestamps
    completions = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed'
    ).all()
    
    # Get focus sessions
    sessions = FocusSession.query.filter_by(user_id=user_id).all()
    
    if not completions and not sessions:
        # Return default productive hours if no data
        return _get_default_productive_hours()
    
    if PANDAS_AVAILABLE:
        return _analyze_with_pandas(completions, sessions)
    else:
        return _analyze_simple(completions, sessions)


def _analyze_with_pandas(completions, sessions):
    """
    Analyze productivity patterns using pandas.
    More sophisticated time-slot aggregation.
    """
    # Build hourly productivity data
    hourly_data = defaultdict(lambda: {'completions': 0, 'efficiency': [], 'focus_score': []})
    
    # Process task completions
    for completion in completions:
        hour = completion.timestamp.hour
        hourly_data[hour]['completions'] += 1
        
        # Calculate efficiency if we have actual vs estimated
        if completion.actual_minutes and completion.task:
            estimated = completion.task.estimated_minutes
            if estimated and estimated > 0:
                efficiency = min(2.0, estimated / completion.actual_minutes)
                hourly_data[hour]['efficiency'].append(efficiency)
    
    # Process focus sessions
    for session in sessions:
        hour = session.start_time.hour
        if session.productivity_score:
            hourly_data[hour]['focus_score'].append(session.productivity_score)
    
    # Calculate composite score for each hour
    hour_scores = []
    for hour in range(24):
        data = hourly_data[hour]
        
        # Base score from completions (normalized)
        completion_score = min(100, data['completions'] * 20)
        
        # Efficiency score (average, scaled to 0-100)
        if data['efficiency']:
            efficiency_score = sum(data['efficiency']) / len(data['efficiency']) * 50
        else:
            efficiency_score = 50
        
        # Focus session score
        if data['focus_score']:
            focus_score = sum(data['focus_score']) / len(data['focus_score'])
        else:
            focus_score = 50
        
        # Composite score
        composite = (completion_score * 0.4) + (efficiency_score * 0.3) + (focus_score * 0.3)
        
        hour_scores.append({
            'hour': hour,
            'score': composite,
            'completions': data['completions']
        })
    
    # Find top 2 windows (consecutive productive hours)
    windows = _find_productive_windows(hour_scores)
    
    return windows[:2] if len(windows) >= 2 else windows


def _analyze_simple(completions, sessions):
    """
    Simple analysis without pandas.
    Basic hourly aggregation.
    """
    hourly_completions = defaultdict(int)
    
    for completion in completions:
        hour = completion.timestamp.hour
        hourly_completions[hour] += 1
    
    for session in sessions:
        hour = session.start_time.hour
        hourly_completions[hour] += session.tasks_completed or 0
    
    # Find peak hours
    if not hourly_completions:
        return _get_default_productive_hours()
    
    sorted_hours = sorted(hourly_completions.items(), key=lambda x: x[1], reverse=True)
    
    windows = []
    used_hours = set()
    
    for hour, count in sorted_hours:
        if hour in used_hours:
            continue
        
        # Create a 2-hour window
        end_hour = (hour + 2) % 24
        windows.append({
            'start_hour': hour,
            'end_hour': end_hour,
            'productivity_score': min(100, count * 25),
            'completions': count,
            'label': _format_time_window(hour, end_hour)
        })
        
        used_hours.add(hour)
        used_hours.add((hour + 1) % 24)
        
        if len(windows) >= 2:
            break
    
    return windows if windows else _get_default_productive_hours()


def _find_productive_windows(hour_scores):
    """
    Find consecutive productive hours to form windows.
    
    Returns windows of 2-3 hours with high combined scores.
    """
    windows = []
    
    # Sort by score to find candidates
    sorted_hours = sorted(hour_scores, key=lambda x: x['score'], reverse=True)
    used_hours = set()
    
    for entry in sorted_hours:
        hour = entry['hour']
        
        if hour in used_hours:
            continue
        
        # Look for a 2-hour window
        next_hour = (hour + 1) % 24
        next_score = next((h['score'] for h in hour_scores if h['hour'] == next_hour), 0)
        
        combined_score = (entry['score'] + next_score) / 2
        
        if combined_score > 40:  # Threshold for "productive"
            windows.append({
                'start_hour': hour,
                'end_hour': (hour + 2) % 24,
                'productivity_score': round(combined_score, 1),
                'completions': entry['completions'],
                'label': _format_time_window(hour, (hour + 2) % 24)
            })
            
            used_hours.add(hour)
            used_hours.add(next_hour)
        
        if len(windows) >= 2:
            break
    
    return windows


def _format_time_window(start_hour, end_hour):
    """Format hour range as readable string."""
    def format_hour(h):
        if h == 0:
            return "12 AM"
        elif h < 12:
            return f"{h} AM"
        elif h == 12:
            return "12 PM"
        else:
            return f"{h - 12} PM"
    
    return f"{format_hour(start_hour)} - {format_hour(end_hour)}"


def _get_default_productive_hours():
    """
    Return default productive windows when no data available.
    Based on common productivity research.
    """
    return [
        {
            'start_hour': 9,
            'end_hour': 11,
            'productivity_score': 70,
            'completions': 0,
            'label': '9 AM - 11 AM',
            'suggestion': 'Morning focus time - great for complex tasks'
        },
        {
            'start_hour': 14,
            'end_hour': 16,
            'productivity_score': 65,
            'completions': 0,
            'label': '2 PM - 4 PM',
            'suggestion': 'Afternoon productivity - good for collaborative work'
        }
    ]


def get_task_suggestions_for_window(user_id, window):
    """
    Suggest task types based on historical patterns for a time window.
    
    Args:
        user_id: User ID
        window: Dict with start_hour and end_hour
    
    Returns:
        list: Suggested task types with reasoning
    """
    from ..models import TaskHistory, Task
    
    start = window.get('start_hour', 9)
    end = window.get('end_hour', 11)
    
    # Get tasks completed in this window
    completions = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed'
    ).all()
    
    # Analyze task characteristics in this time window
    window_tasks = []
    for c in completions:
        if start <= c.timestamp.hour < end or (end < start and (c.timestamp.hour >= start or c.timestamp.hour < end)):
            if c.task:
                window_tasks.append({
                    'importance': c.task.importance,
                    'estimated_minutes': c.task.estimated_minutes,
                    'efficiency': (c.task.estimated_minutes / c.actual_minutes 
                                   if c.actual_minutes and c.actual_minutes > 0 else 1)
                })
    
    if not window_tasks:
        # Default suggestions based on time of day
        if 6 <= start < 12:
            return ['High-focus tasks', 'Complex problem solving', 'Important decisions']
        elif 12 <= start < 17:
            return ['Collaborative tasks', 'Meetings', 'Routine work']
        else:
            return ['Administrative tasks', 'Planning', 'Review work']
    
    # Analyze patterns
    avg_importance = sum(t['importance'] for t in window_tasks) / len(window_tasks)
    avg_duration = sum(t['estimated_minutes'] for t in window_tasks) / len(window_tasks)
    avg_efficiency = sum(t['efficiency'] for t in window_tasks) / len(window_tasks)
    
    suggestions = []
    
    if avg_importance >= 4:
        suggestions.append('High-priority tasks')
    if avg_duration > 45:
        suggestions.append('Longer, focused work')
    elif avg_duration < 20:
        suggestions.append('Quick tasks and admin work')
    if avg_efficiency > 1.2:
        suggestions.append('Tasks you tend to complete efficiently')
    
    return suggestions if suggestions else ['General productive work']


def record_focus_session(user_id, start_time, end_time, tasks_completed, productivity_score=None):
    """
    Record a focus session for learning.
    
    Args:
        user_id: User ID
        start_time: Session start datetime
        end_time: Session end datetime
        tasks_completed: Number of tasks completed
        productivity_score: Optional self-reported score (0-100)
    
    Returns:
        FocusSession: Created session record
    """
    from ..models import db, FocusSession
    
    # Calculate productivity score if not provided
    if productivity_score is None:
        duration_hours = (end_time - start_time).total_seconds() / 3600
        if duration_hours > 0:
            productivity_score = min(100, (tasks_completed / duration_hours) * 30)
        else:
            productivity_score = 50
    
    session = FocusSession(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        tasks_completed=tasks_completed,
        productivity_score=productivity_score
    )
    
    db.session.add(session)
    db.session.commit()
    
    return session


def get_focus_time_insights(user_id):
    """
    Generate comprehensive insights about user's focus patterns.
    
    Returns:
        dict: Insights including best windows, trends, and recommendations
    """
    windows = get_productive_hours(user_id)
    
    insights = {
        'top_windows': windows,
        'recommendations': [],
        'patterns': []
    }
    
    if windows:
        best_window = windows[0]
        insights['recommendations'].append(
            f"Your most productive time is {best_window['label']}. "
            f"Schedule your most important tasks during this window."
        )
        
        if len(windows) > 1:
            second_window = windows[1]
            insights['recommendations'].append(
                f"Your second-best focus time is {second_window['label']}. "
                f"Good for medium-priority tasks."
            )
    
    # Add task suggestions for each window
    for window in windows:
        window['suggested_tasks'] = get_task_suggestions_for_window(user_id, window)
    
    return insights
