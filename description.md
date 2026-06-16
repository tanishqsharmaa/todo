# Project Description

## Project Title
AI-Powered To-Do List MVP

## Overview
This project is a Flask-based productivity web application that combines traditional task management with lightweight AI-driven assistance. It is designed to help users organize tasks, understand their productivity patterns, and receive reminders that adapt to their mood or stress level.

The application uses a modular Flask architecture with SQLAlchemy models, Flask-Login authentication, Flask-WTF CSRF protection, APScheduler background jobs, and simple NLP/heuristic-based AI features for task prioritization, sentiment analysis, and focus-time recommendations.

## Problem Statement
Many to-do apps help users store tasks, but they do not help users decide what to do next, when to do it, or how to stay consistent. This project addresses that gap by combining task management with AI-assisted prioritization, sentiment-aware reminders, and productivity insights.

## Key Objectives
- Provide secure user authentication and personal task management
- Automatically rank tasks by priority using multiple factors
- Analyze task descriptions and reflections to infer user stress or sentiment
- Send reminder notifications with tone adapted to the user’s state
- Track completion history and productivity patterns over time
- Offer a dashboard and analytics view for actionable insights

## Core Features

### 1. User Authentication
- User registration, login, and logout
- Password hashing for secure credential storage
- Session management through Flask-Login

### 2. Task Management
- Create, edit, view, complete, postpone, reopen, and delete tasks
- Store task metadata such as title, description, due date, importance, and estimated duration
- Maintain task history for every action taken

### 3. AI Priority Engine
- Calculates a priority score from 0 to 100
- Considers:
  - due-date urgency
  - user-assigned importance
  - postponement history
  - estimation accuracy patterns
  - task age
- Labels tasks as High, Medium, or Low priority
- Provides human-readable priority explanations

### 4. Sentiment-Aware Task Insights
- Analyzes task descriptions and daily reflections using TextBlob when available
- Falls back to keyword-based sentiment detection if needed
- Maps sentiment to stress levels: Low, Medium, High
- Adjusts reminder tone accordingly: soft, neutral, assertive

### 5. Reminder and Notification System
- Background scheduler checks for due tasks regularly
- Creates notifications for tasks due soon or overdue
- Avoids duplicate reminders
- Lets users mark notifications as read individually or in bulk

### 6. Productivity Analytics
- Tracks task completion trends
- Shows productivity by hour of day
- Measures postponement frequency
- Evaluates time-estimation accuracy
- Generates weekly AI insights and recommendations

### 7. Focus-Time Recommendations
- Analyzes completed tasks and focus sessions
- Detects productive time windows
- Suggests suitable task types for each window
- Supports productivity planning based on user behavior

## Technical Stack
- **Backend:** Python, Flask
- **Database:** SQLite via SQLAlchemy
- **Authentication:** Flask-Login, Werkzeug password hashing
- **Forms/Security:** Flask-WTF, CSRF protection
- **Scheduling:** APScheduler
- **NLP / AI:** TextBlob, heuristic keyword analysis
- **Data Analysis:** pandas, numpy
- **Deployment:** gunicorn
- **Frontend:** HTML, CSS, JavaScript

## Application Structure
- `app/__init__.py` — Flask app factory and extension setup
- `app/models.py` — database models for users, tasks, notifications, sentiment, and focus sessions
- `app/routes/auth.py` — registration, login, logout
- `app/routes/tasks.py` — task CRUD and task lifecycle actions
- `app/routes/dashboard.py` — main dashboard, notifications, reflections
- `app/routes/analytics.py` — productivity analytics and AI insight pages
- `app/ml/priority.py` — priority scoring and explanation logic
- `app/ml/sentiment.py` — sentiment analysis and reminder tone selection
- `app/ml/focus_time.py` — focus-time analysis and task suggestions
- `app/scheduler.py` — reminder job scheduling and notification creation

## Intended Use Case
This project is well suited as a final-year or portfolio project because it demonstrates:
- full-stack Flask development
- database modeling and relationships
- user authentication and security
- background job scheduling
- applied ML/NLP concepts
- analytics and recommendation logic
- a practical productivity-oriented product idea

## Project Value
The main value of this application is its ability to turn a simple to-do list into a smarter assistant. Instead of only storing tasks, it helps users understand task urgency, emotional context, and best times to work, making task management more personalized and actionable.

## Summary
AI-Powered To-Do List MVP is a smart productivity application that blends task tracking, adaptive reminders, sentiment analysis, and productivity analytics into one cohesive Flask project. It is both technically interesting and easy to justify as a real-world problem-solving project proposal.
