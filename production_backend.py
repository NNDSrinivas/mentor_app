"""
Production Backend for AI Mentor - Q&A and Resume Service
Port 8084 - Main service for browser extension and IDE plugins
"""
import os
import sys
import sqlite3
import jwt
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from functools import wraps
try:
    from flask import Flask, request, jsonify, g
    from flask_cors import CORS
except ModuleNotFoundError:  # pragma: no cover - exercised in tests
    from compat.flask_stub import Flask, request, jsonify, g, CORS

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency in tests
    def load_dotenv(*_args, **_kwargs):
        return False

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - optional dependency in tests
    class OpenAI:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            class _Completions:
                def create(self, *c_args, **c_kwargs):
                    raise RuntimeError("OpenAI client not available")

            class _Chat:
                def __init__(self) -> None:
                    self.completions = _Completions()

            self.chat = _Chat()

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency in tests
    class _RequestsStub:
        class _Response:
            status_code = 200
            text = ""

            def json(self) -> dict:
                return {}

        def post(self, *args, **kwargs):
            return self._Response()

    requests = _RequestsStub()  # type: ignore[assignment]

try:
    from backend.calendar_integration import CalendarIntegration
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional integration
    CalendarIntegration = None  # type: ignore[assignment]

# Import AI assistant functionality
try:
    from app.ai_assistant import AIAssistant
    AI_ASSISTANT_AVAILABLE = True
except ImportError as e:
    print(f"AI Assistant not available: {e}")
    AI_ASSISTANT_AVAILABLE = False

# Load environment variables
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    print("Error: JWT_SECRET environment variable not set. Exiting.")
    sys.exit(1)

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://meet.google.com",
            "https://teams.microsoft.com",
            "https://*.zoom.us",
            "http://localhost:*"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
app.config['SECRET_KEY'] = JWT_SECRET
app.config['DATABASE'] = os.getenv('DATABASE_PATH', 'production_mentor.db')

# OpenAI Configuration
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# AI Assistant Configuration
ai_assistant = None
if AI_ASSISTANT_AVAILABLE:
    try:
        ai_assistant = AIAssistant()
    except Exception as e:
        print(f"Failed to initialize AI Assistant: {e}")
        ai_assistant = None


def init_db():
    """Initialize the database."""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            subscription TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # Usage tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            month TEXT NOT NULL,
            questions_used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, month)
        )
    ''')

    # Resume storage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            user_id TEXT PRIMARY KEY,
            resume_text TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Scheduled sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            meeting_url TEXT,
            calendar_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()


def get_db():
    """Get database connection."""
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection."""
    if hasattr(g, 'db'):
        g.db.close()


def hash_password(password):
    """Hash a password."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, password_hash):
    """Verify a password against its hash."""
    return hash_password(password) == password_hash


def generate_token(user_id):
    """Generate JWT token for user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token):
    """Verify JWT token and return user_id."""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def auth_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow browser extension requests in development
        allow_browser_extension = os.getenv('ALLOW_BROWSER_EXTENSION', 'false').lower() == 'true'

        token = request.headers.get('Authorization')
        if not token:
            if allow_browser_extension:
                # For browser extension compatibility, use a default user
                g.user_id = 'browser_extension_user'
                return f(*args, **kwargs)
            return jsonify({'error': 'No token provided'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401

        g.user_id = user_id
        return f(*args, **kwargs)

    return decorated


def get_usage_limits(subscription):
    """Get usage limits based on subscription."""
    limits = {
        'free': 10,
        'pro': 500,
        'enterprise': float('inf')
    }
    return limits.get(subscription, 10)


def check_usage_limit(user_id):
    """Check if user has exceeded usage limit."""
    # Allow unlimited usage for browser extension in development
    if user_id == 'browser_extension_user':
        return True

    db = get_db()
    cursor = db.cursor()

    # Get user subscription
    cursor.execute('SELECT subscription FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        return False

    subscription = user['subscription']
    limit = get_usage_limits(subscription)

    if limit == float('inf'):
        return True

    # Get current month usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT questions_used FROM usage WHERE user_id = ? AND month = ?',
                   (user_id, current_month))
    usage = cursor.fetchone()

    current_usage = usage['questions_used'] if usage else 0
    return current_usage < limit


def increment_usage(user_id):
    """Increment usage count for user."""
    # Skip usage tracking for browser extension in development
    if user_id == 'browser_extension_user':
        return

    db = get_db()
    cursor = db.cursor()

    current_month = datetime.now().strftime('%Y-%m')

    # Insert or update usage
    cursor.execute('''
        INSERT OR REPLACE INTO usage (id, user_id, month, questions_used)
        VALUES (?, ?, ?, COALESCE((SELECT questions_used FROM usage WHERE user_id = ? AND month = ?), 0) + 1)
    ''', (str(uuid.uuid4()), user_id, current_month, user_id, current_month))

    db.commit()


def notify_clients(message: dict) -> None:
    """Best-effort notification to external clients via HTTP API."""
    url = os.getenv('CLIENT_NOTIFY_URL')
    if not url:
        return
    try:  # pragma: no cover - network failures are ignored
        requests.post(url, json=message, timeout=5)
    except Exception:
        pass

# Routes


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Mentor Q&A Service',
        'port': 8084,
        'ai_assistant_available': ai_assistant is not None,
        'openai_configured': bool(os.getenv('OPENAI_API_KEY'))
    })


@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    email = data['email'].lower().strip()
    password = data['password']

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    cursor = db.cursor()

    # Check if user exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        return jsonify({'error': 'User already exists'}), 409

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)

    cursor.execute('''
        INSERT INTO users (id, email, password_hash, subscription)
        VALUES (?, ?, ?, 'free')
    ''', (user_id, email, password_hash))

    db.commit()

    # Generate token
    token = generate_token(user_id)

    return jsonify({
        'message': 'User registered successfully',
        'token': token,
        'user_id': user_id,
        'subscription': 'free'
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """Login user."""
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    email = data['email'].lower().strip()
    password = data['password']

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id, password_hash, subscription FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()

    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Update last login
    cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
    db.commit()

    # Generate token
    token = generate_token(user['id'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user_id': user['id'],
        'subscription': user['subscription']
    })


@app.route('/api/user/profile', methods=['GET'])
@auth_required
def get_profile():
    """Get user profile and usage."""
    db = get_db()
    cursor = db.cursor()

    # Get user info
    cursor.execute('SELECT email, subscription, created_at FROM users WHERE id = ?', (g.user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Get current month usage
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT questions_used FROM usage WHERE user_id = ? AND month = ?',
                   (g.user_id, current_month))
    usage = cursor.fetchone()

    current_usage = usage['questions_used'] if usage else 0
    limit = get_usage_limits(user['subscription'])

    return jsonify({
        'email': user['email'],
        'subscription': user['subscription'],
        'created_at': user['created_at'],
        'usage': {
            'current_month': current_usage,
            'limit': limit if limit != float('inf') else 'unlimited',
            'remaining': max(0, limit - current_usage) if limit != float('inf') else 'unlimited'
        }
    })


@app.route('/api/ask', methods=['POST'])
@auth_required
def ask_question():
    """Ask AI a question."""
    data = request.get_json()

    if not data or not data.get('question'):
        return jsonify({'error': 'Question is required'}), 400

    # Check usage limit
    if not check_usage_limit(g.user_id):
        return jsonify({'error': 'Usage limit exceeded for your subscription'}), 429

    question = data['question']
    interview_mode = data.get('interview_mode', False)

    try:
        # Get user's resume if available
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT resume_text FROM resumes WHERE user_id = ?', (g.user_id,))
        resume_row = cursor.fetchone()
        resume_text = resume_row['resume_text'] if resume_row else None

        # Generate response using OpenAI directly (simplified for production)
        messages = [
            {
                "role": "system",
                "content": ("You are an expert AI assistant helping with interview preparation, "
                            "coding questions, and technical discussions. Provide clear, "
                            "concise, and accurate answers.")
            }
        ]

        if resume_text and interview_mode:
            messages.append({
                "role": "system",
                "content": (f"User's background (from resume): {resume_text[:1000]}... "
                            f"Use this context to personalize your response.")
            })

        if interview_mode:
            messages.append({
                "role": "system",
                "content": ("You are helping with interview preparation. "
                            "Focus on clear explanations and practical examples.")
            })

        messages.append({"role": "user", "content": question})

        chat_completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        response = chat_completion.choices[0].message.content

        # Increment usage
        increment_usage(g.user_id)

        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'interview_mode': interview_mode
        })

    except Exception as e:
        print(f"Error generating response: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500


@app.route('/api/resume', methods=['POST'])
@auth_required
def upload_resume():
    """Upload or update user resume."""
    data = request.get_json()

    if not data or not data.get('resume_text'):
        return jsonify({'error': 'Resume text is required'}), 400

    resume_text = data['resume_text'].strip()

    if len(resume_text) < 50:
        return jsonify({'error': 'Resume text too short'}), 400

    db = get_db()
    cursor = db.cursor()

    # Insert or update resume
    cursor.execute('''
        INSERT OR REPLACE INTO resumes (user_id, resume_text, uploaded_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (g.user_id, resume_text))

    db.commit()

    return jsonify({
        'message': 'Resume uploaded successfully',
        'length': len(resume_text)
    })


@app.route('/api/resume', methods=['GET'])
@auth_required
def get_resume():
    """Get user resume."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT resume_text, uploaded_at FROM resumes WHERE user_id = ?', (g.user_id,))
    resume = cursor.fetchone()

    if not resume:
        return jsonify({'error': 'No resume found'}), 404

    return jsonify({
        'resume_text': resume['resume_text'],
        'uploaded_at': resume['uploaded_at'],
        'length': len(resume['resume_text'])
    })


@app.route('/api/resume', methods=['DELETE'])
@auth_required
def delete_resume():
    """Delete user resume."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute('DELETE FROM resumes WHERE user_id = ?', (g.user_id,))
    db.commit()

    return jsonify({'message': 'Resume deleted successfully'})


@app.route('/api/sessions', methods=['POST'])
@auth_required
def create_session():
    """Schedule a session and store it in the database."""
    data = request.get_json() or {}
    try:
        title = data['title']
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
    except KeyError:
        return jsonify({'error': 'Missing required fields'}), 400

    attendees = data.get('attendees', [])
    platform = data.get('platform', 'zoom')
    description = data.get('description', '')
    location = data.get('location', '')

    if CalendarIntegration is None:
        return jsonify({'error': 'Calendar integration unavailable'}), 503

    calendar = CalendarIntegration()
    event = calendar.schedule_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        attendees=attendees,
        platform=platform,
        description=description,
        location=location,
    )

    db = get_db()
    cursor = db.cursor()
    session_id = str(uuid.uuid4())
    cursor.execute(
        ('INSERT INTO sessions (id, user_id, title, start_time, end_time, '
         'meeting_url, calendar_event_id) VALUES (?, ?, ?, ?, ?, ?, ?)'),
        (
            session_id,
            g.user_id,
            title,
            start_time.isoformat(),
            end_time.isoformat(),
            event.meeting_url,
            event.id,
        ),
    )
    db.commit()

    notify_clients({'session_id': session_id, 'meeting_url': event.meeting_url})

    return (
        jsonify(
            {
                'session_id': session_id,
                'meeting_url': event.meeting_url,
                'calendar_event_id': event.id,
            }
        ),
        201,
    )

# Error handlers


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Initialize database
    init_db()

    print("🚀 Starting AI Mentor Q&A Service on port 8084...")
    print("📝 Available endpoints:")
    print("   POST /api/register - Register new user")
    print("   POST /api/login - Login user")
    print("   GET  /api/user/profile - Get user profile")
    print("   POST /api/ask - Ask AI a question")
    print("   POST /api/resume - Upload resume")
    print("   GET  /api/resume - Get resume")
    print("   GET  /api/health - Health check")

    # Run the app
    port = int(os.getenv('API_PORT', 8084))
    debug = os.getenv('FLASK_ENV') == 'development'

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )
