

from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from ..models import db, Task, TaskHistory, SentimentLog, FocusSession
from ..ml.focus_time import get_focus_time_insights
from ..ml.priority import get_priority_explanation

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/')
@login_required
def index():
    """
    Main analytics dashboard.
    
    Shows comprehensive productivity metrics and AI insights.
    """
    user_id = current_user.id
    
    # Date ranges
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # ==========================================================
    # TASK STATISTICS
    # ==========================================================
    total_tasks = Task.query.filter_by(user_id=user_id).count()
    pending_tasks = Task.query.filter_by(user_id=user_id, status='pending').count()
    completed_tasks = Task.query.filter_by(user_id=user_id, status='completed').count()
    postponed_tasks = Task.query.filter_by(user_id=user_id, status='postponed').count()
    
    # Completion rate
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    task_stats = {
        'total': total_tasks,
        'pending': pending_tasks,
        'completed': completed_tasks,
        'postponed': postponed_tasks,
        'completion_rate': round(completion_rate, 1)
    }
    
    # ==========================================================
    # PRODUCTIVITY BY HOUR
    # ==========================================================
    hourly_completions = defaultdict(int)
    
    completions = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed'
    ).all()
    
    for c in completions:
        hourly_completions[c.timestamp.hour] += 1
    
    # Format for chart (all 24 hours)
    productivity_by_hour = [
        {'hour': h, 'count': hourly_completions.get(h, 0)}
        for h in range(24)
    ]
    
    # ==========================================================
    # DELAY FREQUENCY (POSTPONEMENTS)
    # ==========================================================
    postponements = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'postponed'
    ).all()
    
    # Group by day of week
    delay_by_day = defaultdict(int)
    for p in postponements:
        day_name = p.timestamp.strftime('%A')
        delay_by_day[day_name] += 1
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    delay_frequency = [
        {'day': day, 'count': delay_by_day.get(day, 0)}
        for day in days_order
    ]
    
    # ==========================================================
    # WEEKLY TRENDS
    # ==========================================================
    weekly_completions = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed',
        TaskHistory.timestamp >= week_ago
    ).count()
    
    weekly_creations = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'created',
        TaskHistory.timestamp >= week_ago
    ).count()
    
    weekly_stats = {
        'completed': weekly_completions,
        'created': weekly_creations,
        'net_progress': weekly_completions - weekly_creations
    }
    
    # ==========================================================
    # ESTIMATION ACCURACY
    # ==========================================================
    accuracy_data = []
    completions_with_time = TaskHistory.query.join(Task).filter(
        Task.user_id == user_id,
        TaskHistory.action == 'completed',
        TaskHistory.actual_minutes.isnot(None)
    ).all()
    
    total_estimated = 0
    total_actual = 0
    
    for c in completions_with_time:
        if c.task and c.task.estimated_minutes:
            total_estimated += c.task.estimated_minutes
            total_actual += c.actual_minutes
    
    if total_estimated > 0:
        accuracy_ratio = total_actual / total_estimated
        if accuracy_ratio > 1.2:
            accuracy_insight = "You tend to underestimate task duration. Try adding 20% buffer."
        elif accuracy_ratio < 0.8:
            accuracy_insight = "You often overestimate. Your efficiency is better than expected!"
        else:
            accuracy_insight = "Your time estimates are quite accurate. Keep it up!"
    else:
        accuracy_ratio = 1.0
        accuracy_insight = "Start tracking actual completion times to improve estimates."
    
    estimation_accuracy = {
        'ratio': round(accuracy_ratio, 2),
        'insight': accuracy_insight,
        'total_estimated': total_estimated,
        'total_actual': total_actual
    }
    
    # ==========================================================
    # AI INSIGHTS
    # ==========================================================
    focus_insights = get_focus_time_insights(user_id)
    
    # Generate weekly AI insights
    ai_insights = generate_weekly_insights(user_id, task_stats, weekly_stats, estimation_accuracy)
    
    return render_template(
        'analytics/index.html',
        task_stats=task_stats,
        productivity_by_hour=productivity_by_hour,
        delay_frequency=delay_frequency,
        weekly_stats=weekly_stats,
        estimation_accuracy=estimation_accuracy,
        focus_insights=focus_insights,
        ai_insights=ai_insights
    )


def generate_weekly_insights(user_id, task_stats, weekly_stats, estimation):
    """
    Generate textual AI insights based on user's data.
    
    These insights are designed to be:
    1. Actionable
    2. Personalized
    3. Encouraging
    
    Args:
        user_id: User ID
        task_stats: Overall task statistics
        weekly_stats: This week's statistics
        estimation: Estimation accuracy data
    
    Returns:
        list: List of insight strings
    """
    insights = []
    
    # Completion rate insight
    if task_stats['completion_rate'] >= 80:
        insights.append({
            'type': 'success',
            'title': 'Excellent Completion Rate',
            'text': f"You've completed {task_stats['completion_rate']}% of your tasks. Outstanding productivity!"
        })
    elif task_stats['completion_rate'] >= 50:
        insights.append({
            'type': 'info',
            'title': 'Good Progress',
            'text': f"Your completion rate is {task_stats['completion_rate']}%. Consider breaking larger tasks into smaller ones."
        })
    elif task_stats['total'] > 0:
        insights.append({
            'type': 'warning',
            'title': 'Room for Improvement',
            'text': "Your completion rate is below 50%. Focus on completing high-priority tasks first."
        })
    
    # Weekly progress insight
    if weekly_stats['net_progress'] > 0:
        insights.append({
            'type': 'success',
            'title': 'Making Progress',
            'text': f"This week you completed {weekly_stats['net_progress']} more tasks than you created. Great momentum!"
        })
    elif weekly_stats['net_progress'] < -5:
        insights.append({
            'type': 'warning',
            'title': 'Task Accumulation',
            'text': "You're creating more tasks than completing. Consider a task review session."
        })
    
    # Postponement insight
    if task_stats['postponed'] > task_stats['completed'] * 0.3:
        insights.append({
            'type': 'info',
            'title': 'High Postponement Rate',
            'text': "You're postponing many tasks. This might indicate overcommitment or task sizing issues."
        })
    
    # Time estimation insight
    if estimation['ratio'] > 1.3:
        insights.append({
            'type': 'warning',
            'title': 'Underestimating Time',
            'text': f"Tasks take {int((estimation['ratio'] - 1) * 100)}% longer than estimated. Add buffer time."
        })
    
    # Pending tasks insight
    if task_stats['pending'] > 20:
        insights.append({
            'type': 'info',
            'title': 'Large Backlog',
            'text': f"You have {task_stats['pending']} pending tasks. Consider archiving or delegating some."
        })
    
    # Default insight if no specific ones
    if not insights:
        insights.append({
            'type': 'info',
            'title': 'Getting Started',
            'text': "Keep using the app to build your productivity profile. AI insights improve with more data!"
        })
    
    return insights


@analytics_bp.route('/task/<int:task_id>/priority-explanation')
@login_required
def priority_explanation(task_id):
    """
    Show detailed explanation of a task's priority score.
    
    Useful for understanding AI decisions and viva demonstration.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    explanation = get_priority_explanation(task, current_user.id)
    
    return render_template('analytics/priority_explanation.html', explanation=explanation, task=task)
