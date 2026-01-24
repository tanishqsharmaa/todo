

from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from ..models import db, Task, Notification, SentimentLog
from ..ml.focus_time import get_focus_time_insights
from ..ml.sentiment import analyze_daily_reflection, get_reminder_tone
from ..scheduler import get_unread_notifications, mark_notification_read, mark_all_notifications_read

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """
    Main dashboard view.
    
    Displays:
    - High priority pending tasks
    - Recent notifications
    - Focus time recommendations
    - Quick stats
    """
    # Get high priority tasks (top 5)
    high_priority_tasks = Task.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).order_by(
        Task.priority_score.desc()
    ).limit(5).all()
    
    # Get tasks due today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    due_today = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status == 'pending',
        Task.due_date >= today_start,
        Task.due_date < today_end
    ).count()
    
    # Get overdue tasks
    overdue_count = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status == 'pending',
        Task.due_date < today_start
    ).count()
    
    # Get unread notifications
    notifications = get_unread_notifications(current_user.id, limit=5)
    
    # Get focus time insights
    focus_insights = get_focus_time_insights(current_user.id)
    
    # Get current reminder tone (for display)
    current_tone = get_reminder_tone(current_user.id)
    
    # Quick stats
    stats = {
        'total_pending': Task.query.filter_by(user_id=current_user.id, status='pending').count(),
        'completed_today': Task.query.join(Task.history).filter(
            Task.user_id == current_user.id,
            Task.history.any(action='completed', timestamp=today_start)
        ).count(),
        'due_today': due_today,
        'overdue': overdue_count
    }
    
    return render_template(
        'dashboard/index.html',
        tasks=high_priority_tasks,
        notifications=notifications,
        focus_insights=focus_insights,
        current_tone=current_tone,
        stats=stats
    )


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications."""
    all_notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    
    return render_template('dashboard/notifications.html', notifications=all_notifications)


@dashboard_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a single notification as read."""
    mark_notification_read(notification_id, current_user.id)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'status': 'ok'}
    
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    mark_all_notifications_read(current_user.id)
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/reflection', methods=['GET', 'POST'])
@login_required
def daily_reflection():
    """
    Daily reflection input for sentiment analysis.
    
    User can write how they're feeling, which affects reminder tones.
    """
    analysis = None
    
    if request.method == 'POST':
        reflection_text = request.form.get('reflection', '').strip()
        
        if reflection_text:
            analysis = analyze_daily_reflection(current_user.id, reflection_text)
            flash('Reflection recorded. Your reminder tone has been adjusted.', 'success')
        else:
            flash('Please enter some text for your reflection.', 'error')
    
    # Get recent sentiment logs
    recent_sentiments = SentimentLog.query.filter_by(
        user_id=current_user.id
    ).order_by(
        SentimentLog.timestamp.desc()
    ).limit(7).all()
    
    return render_template(
        'dashboard/reflection.html',
        analysis=analysis,
        recent_sentiments=recent_sentiments
    )
