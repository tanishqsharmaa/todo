

import os
from app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment or use defaults
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║         AI-Powered To-Do List MVP                            ║
    ║         Built with Flask + SQLite                            ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Running on: http://{host}:{port}                            
    ║  Debug mode: {debug}                                          
    ║                                                              ║
    ║  Features:                                                   ║
    ║  • AI Priority Prediction Engine                             ║
    ║  • Sentiment-Aware Reminders                                 ║
    ║  • Focus Time Recommendations                                ║
    ║  • Analytics Dashboard                                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Run the Flask development server
    app.run(host=host, port=port, debug=debug)
