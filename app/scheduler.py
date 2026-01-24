"""
Reminder & Notification Scheduler for AI-Powered To-Do List MVP

Uses APScheduler to run background jobs that:
1. Check for upcoming due tasks
2. Generate sentiment-aware reminders
3. Create notifications in the database

FEATURES:
- Runs every X minutes (configurable)
- Reminder tone depends on user's sentiment state
- Avoids duplicate notifications
- Logs all reminder decisions for transparency
"""

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# Global scheduler instance
scheduler = None


def init_scheduler(app):
    """
    Initialize and start the background scheduler.
    
    Args:
        app: Flask application instance
    """
    global scheduler
    
    if scheduler is not None:
        return
    
    scheduler = BackgroundScheduler()
    
    # Get check interval from config (default: 5 minutes)
    interval = app.config.get('REMINDER_CHECK_INTERVAL', 5)
    
    # Add job with app context
    scheduler.add_job(
        func=lambda: check_due_tasks(app),
        trigger='interval',
        minutes=interval,
        id='check_due_tasks',
        name='Check for due tasks and create reminders',
        replace_existing=True
    )
    
    scheduler.start()
    app.logger.info(f'Scheduler started. Checking tasks every {interval} minutes.')


def check_due_tasks(app):
    """
    Background job to check for tasks that need reminders.
    
    Logic:
    1. Find tasks due within the next 24 hours
    2. Check if reminder already sent recently
    3. Generate sentiment-appropriate reminder
    4. Create notification in database
    """
    with app.app_context():
        from .models import db, Task, Notification, User
        from .ml.sentiment import get_reminder_tone, get_reminder_message
        
        now = datetime.utcnow()
        reminder_window = now + timedelta(hours=24)
        
        # Get all users
        users = User.query.all()
        
        for user in users:
            # Get pending tasks due within 24 hours
            due_tasks = Task.query.filter(
                Task.user_id == user.id,
                Task.status == 'pending',
                Task.due_date.isnot(None),
                Task.due_date <= reminder_window,
                Task.due_date >= now - timedelta(hours=24)  # Include overdue up to 24h
            ).all()
            
            for task in due_tasks:
                # Check if we already sent a reminder in the last 4 hours
                recent_notification = Notification.query.filter(
                    Notification.user_id == user.id,
                    Notification.task_id == task.id,
                    Notification.created_at >= now - timedelta(hours=4)
                ).first()
                
                if recent_notification:
                    continue  # Skip - already reminded
                
                # Get appropriate tone based on user's sentiment
                tone = get_reminder_tone(user.id)
                
                # Generate message
                message = get_reminder_message(task, tone)
                
                # Add context about due date
                if task.days_until_due is not None:
                    if task.days_until_due < 0:
                        message += f" (Overdue by {abs(task.days_until_due)} day(s))"
                    elif task.days_until_due == 0:
                        message += " (Due today!)"
                    else:
                        message += f" (Due in {task.days_until_due} day(s))"
                
                # Create notification
                notification = Notification(
                    user_id=user.id,
                    task_id=task.id,
                    message=message,
                    tone=tone
                )
                db.session.add(notification)
        
        db.session.commit()
        app.logger.info(f'Reminder check completed at {now}')


def get_unread_notifications(user_id, limit=10):
    """
    Get unread notifications for a user.
    
    Args:
        user_id: User ID
        limit: Maximum notifications to return
    
    Returns:
        list: Notification objects
    """
    from .models import Notification
    
    return Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(
        Notification.created_at.desc()
    ).limit(limit).all()


def mark_notification_read(notification_id, user_id):
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        user_id: User ID (for security check)
    
    Returns:
        bool: Success status
    """
    from .models import db, Notification
    
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()
    
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user."""
    from .models import db, Notification
    
    Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()


def create_manual_notification(user_id, message, tone='neutral', task_id=None):
    """
    Create a notification manually (e.g., for system messages).
    
    Args:
        user_id: User ID
        message: Notification message
        tone: Message tone
        task_id: Optional related task
    
    Returns:
        Notification: Created notification
    """
    from .models import db, Notification
    
    notification = Notification(
        user_id=user_id,
        message=message,
        tone=tone,
        task_id=task_id
    )
    db.session.add(notification)
    db.session.commit()
    
    return notification
