"""
Flask Application Factory for AI-Powered To-Do List MVP

This module initializes the Flask app with:
- SQLAlchemy for database
- Flask-Login for authentication
- Flask-WTF for CSRF protection
- Blueprint registration for modular routes
- APScheduler for background reminder jobs
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from .models import db, User

# Initialize extensions
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config=None):
    """
    Application factory pattern for Flask.
    
    Args:
        config: Optional configuration dictionary
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{os.path.join(app.instance_path, "app.db")}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        # Scheduler settings
        SCHEDULER_API_ENABLED=False,
        REMINDER_CHECK_INTERVAL=5,  # Minutes between reminder checks
    )
    
    # Override with custom config if provided
    if config:
        app.config.from_mapping(config)
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.tasks import tasks_bp
    from .routes.dashboard import dashboard_bp
    from .routes.analytics import analytics_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize scheduler (only in main process)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        from .scheduler import init_scheduler
        init_scheduler(app)
    
    return app
