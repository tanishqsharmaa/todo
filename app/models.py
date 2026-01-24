

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model for authentication.
    Single-user scope but designed for extensibility.
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sentiment_logs = db.relationship('SentimentLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    focus_sessions = db.relationship('FocusSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and store password securely using Werkzeug."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Task(db.Model):
    """
    Core task entity containing all task attributes.
    
    AI-relevant fields:
    - importance: User-assigned priority (1-5)
    - estimated_minutes: For comparing with actual duration
    - status: Tracks task lifecycle
    - created_at: Used to calculate task age
    """
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    estimated_minutes = db.Column(db.Integer, default=30)
    importance = db.Column(db.Integer, default=3)  # 1-5 scale
    status = db.Column(db.String(20), default='pending')  # pending, completed, postponed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # AI-computed fields (cached for performance)
    priority_score = db.Column(db.Float, default=50.0)  # 0-100 computed score
    priority_label = db.Column(db.String(10), default='Medium')  # High/Medium/Low
    
    # Relationships
    history = db.relationship('TaskHistory', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def days_until_due(self):
        """Calculate days remaining until due date. Negative if overdue."""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days
    
    @property
    def task_age_days(self):
        """Calculate how many days since task was created."""
        delta = datetime.utcnow() - self.created_at
        return delta.days
    
    def __repr__(self):
        return f'<Task {self.title[:30]}>'


class TaskHistory(db.Model):
    """
    Tracks every interaction with a task for AI learning.
    
    Actions tracked:
    - created: Task creation
    - completed: Task marked as done
    - postponed: Task deadline extended
    - edited: Task details modified
    
    actual_minutes is recorded on completion to compare with estimates.
    This data is critical for the priority prediction engine.
    """
    __tablename__ = 'task_history'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    action = db.Column(db.String(20), nullable=False)  # created, completed, postponed, edited
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actual_minutes = db.Column(db.Integer, nullable=True)  # Recorded on completion
    notes = db.Column(db.Text, nullable=True)  # Optional context
    
    def __repr__(self):
        return f'<TaskHistory {self.action} at {self.timestamp}>'


class SentimentLog(db.Model):
    """
    Stores sentiment analysis results for reminder tone adjustment.
    
    Sources:
    - Task descriptions
    - Daily reflection input
    
    The stress_level determines reminder tone:
    - High stress -> softer, encouraging reminders
    - Low stress -> direct, assertive reminders
    """
    __tablename__ = 'sentiment_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)  # -1 to +1
    stress_level = db.Column(db.String(10), nullable=False)  # Low, Medium, High
    source_text = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<SentimentLog {self.stress_level} at {self.timestamp}>'


class FocusSession(db.Model):
    """
    Records work sessions to identify productive time windows.
    
    Used by focus_time.py to:
    - Aggregate productivity by hour of day
    - Recommend optimal focus times
    - Suggest task types per time window
    """
    __tablename__ = 'focus_session'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    productivity_score = db.Column(db.Float, default=0.0)  # 0-100
    tasks_completed = db.Column(db.Integer, default=0)
    
    @property
    def duration_minutes(self):
        """Calculate session duration in minutes."""
        if not self.end_time:
            return 0
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    def __repr__(self):
        return f'<FocusSession {self.start_time}>'


class Notification(db.Model):
    """
    Stores notifications for display in UI.
    Generated by the scheduler based on due tasks and sentiment.
    """
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(20), default='neutral')  # soft, neutral, assertive
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    
    def __repr__(self):
        return f'<Notification {self.message[:30]}>'
