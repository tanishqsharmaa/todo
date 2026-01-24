
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from ..models import db, Task, TaskHistory, SentimentLog
from ..ml.priority import calculate_priority
from ..ml.sentiment import analyze_sentiment

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def log_task_action(task, action, actual_minutes=None, notes=None):
    """
    Helper to log every task interaction.
    This data feeds the AI priority prediction engine.
    
    Args:
        task: Task instance
        action: One of 'created', 'completed', 'postponed', 'edited'
        actual_minutes: Time spent (for completions)
        notes: Optional context
    """
    history = TaskHistory(
        task_id=task.id,
        action=action,
        actual_minutes=actual_minutes,
        notes=notes
    )
    db.session.add(history)


def update_task_priority(task):
    """
    Recalculate and update task's AI priority score.
    Called on task creation, edit, and periodic updates.
    """
    score, label = calculate_priority(task, current_user.id)
    task.priority_score = score
    task.priority_label = label


@tasks_bp.route('/')
@login_required
def list_tasks():
    """
    List all tasks for current user.
    Sorted by priority score (highest first).
    """
    # Update priorities for pending tasks
    pending_tasks = Task.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).all()
    
    for task in pending_tasks:
        update_task_priority(task)
    db.session.commit()
    
    # Get all tasks sorted by priority
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.status.asc(),  # pending first
        Task.priority_score.desc()
    ).all()
    
    return render_template('tasks/list.html', tasks=tasks)


@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """
    Create a new task.
    Analyzes description sentiment and logs creation.
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '')
        estimated_minutes = request.form.get('estimated_minutes', 30, type=int)
        importance = request.form.get('importance', 3, type=int)
        
        # Validation
        if not title:
            flash('Task title is required.', 'error')
            return render_template('tasks/create.html')
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid due date format.', 'error')
                    return render_template('tasks/create.html')
        
        # Create task
        task = Task(
            user_id=current_user.id,
            title=title,
            description=description,
            due_date=due_date,
            estimated_minutes=max(1, estimated_minutes),
            importance=max(1, min(5, importance)),
            status='pending'
        )
        
        db.session.add(task)
        db.session.flush()  # Get task ID before logging
        
        # Log creation
        log_task_action(task, 'created')
        
        # Analyze sentiment if description provided
        if description:
            score, stress = analyze_sentiment(description)
            sentiment_log = SentimentLog(
                user_id=current_user.id,
                score=score,
                stress_level=stress,
                source_text=description[:500]  # Limit stored text
            )
            db.session.add(sentiment_log)
        
        # Calculate initial priority
        update_task_priority(task)
        
        db.session.commit()
        
        flash(f'Task "{title}" created successfully!', 'success')
        return redirect(url_for('tasks.list_tasks'))
    
    return render_template('tasks/create.html')


@tasks_bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    """View a single task with its history."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    # Update priority
    update_task_priority(task)
    db.session.commit()
    
    # Get task history
    history = TaskHistory.query.filter_by(task_id=task.id).order_by(
        TaskHistory.timestamp.desc()
    ).all()
    
    return render_template('tasks/view.html', task=task, history=history)


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit an existing task."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date_str = request.form.get('due_date', '')
        estimated_minutes = request.form.get('estimated_minutes', 30, type=int)
        importance = request.form.get('importance', 3, type=int)
        
        if not title:
            flash('Task title is required.', 'error')
            return render_template('tasks/edit.html', task=task)
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid due date format.', 'error')
                    return render_template('tasks/edit.html', task=task)
        
        # Update task
        task.title = title
        task.description = description
        task.due_date = due_date
        task.estimated_minutes = max(1, estimated_minutes)
        task.importance = max(1, min(5, importance))
        
        # Log edit
        log_task_action(task, 'edited')
        
        # Update priority
        update_task_priority(task)
        
        db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    return render_template('tasks/edit.html', task=task)


@tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """
    Mark task as completed.
    Records actual time spent for AI learning.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    actual_minutes = request.form.get('actual_minutes', type=int)
    
    task.status = 'completed'
    
    # Log completion with actual duration
    log_task_action(task, 'completed', actual_minutes=actual_minutes)
    
    db.session.commit()
    
    flash(f'Task "{task.title}" marked as complete!', 'success')
    return redirect(url_for('tasks.list_tasks'))


@tasks_bp.route('/<int:task_id>/postpone', methods=['POST'])
@login_required
def postpone_task(task_id):
    """
    Postpone task to a later date.
    Logs postponement for AI priority adjustment.
    """
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    days = request.form.get('days', 1, type=int)
    
    if task.due_date:
        task.due_date = task.due_date + timedelta(days=days)
    else:
        task.due_date = datetime.utcnow() + timedelta(days=days)
    
    task.status = 'postponed'
    
    # Log postponement - this increases priority in future predictions
    log_task_action(task, 'postponed', notes=f'Postponed by {days} days')
    
    # Recalculate priority (will be higher due to postponement history)
    update_task_priority(task)
    
    db.session.commit()
    
    flash(f'Task "{task.title}" postponed by {days} day(s).', 'info')
    return redirect(url_for('tasks.list_tasks'))


@tasks_bp.route('/<int:task_id>/reopen', methods=['POST'])
@login_required
def reopen_task(task_id):
    """Reopen a completed or postponed task."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    task.status = 'pending'
    log_task_action(task, 'edited', notes='Reopened task')
    update_task_priority(task)
    
    db.session.commit()
    
    flash(f'Task "{task.title}" reopened.', 'info')
    return redirect(url_for('tasks.list_tasks'))


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task and its history."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    
    title = task.title
    db.session.delete(task)
    db.session.commit()
    
    flash(f'Task "{title}" deleted.', 'info')
    return redirect(url_for('tasks.list_tasks'))
