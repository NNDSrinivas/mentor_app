#!/usr/bin/env python3
"""
Simple AI Mentor Web Interface for Testing
"""

from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
import asyncio
import os
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from app.ai_assistant import AIAssistant
from app.config import Config

# Setup logging
logger = logging.getLogger(__name__)

# Import the new ProfileManager
try:
    from app.profile_manager import ProfileManager
    PROFILE_MANAGER_AVAILABLE = True
    print("✅ ProfileManager module imported successfully")
except ImportError as e:
    print(f"⚠️ ProfileManager not available - resume features disabled")
    print(f"Import error details: {e}")
    PROFILE_MANAGER_AVAILABLE = False
except Exception as e:
    print(f"⚠️ ProfileManager not available - unexpected error: {e}")
    import traceback
    traceback.print_exc()
    PROFILE_MANAGER_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Configure upload settings
UPLOAD_FOLDER = 'data/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ai_assistant = AIAssistant()

# Initialize ProfileManager if available
if PROFILE_MANAGER_AVAILABLE:
    try:
        profile_manager = ProfileManager()
        print("✅ ProfileManager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ProfileManager: {e}")
        import traceback
        traceback.print_exc()
        profile_manager = None
        PROFILE_MANAGER_AVAILABLE = False
else:
    profile_manager = None
    print("❌ ProfileManager not available")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main web interface."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 AI Mentor Assistant</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                max-width: 900px; margin: 0 auto; padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #333; margin: 0; }
            .header p { color: #666; margin: 10px 0; }
            .status { 
                display: inline-block; 
                padding: 5px 15px; 
                background: #d4edda; 
                color: #155724; 
                border-radius: 20px; 
                font-size: 14px; 
            }
            .chat-box { 
                height: 400px; 
                border: 2px solid #e9ecef; 
                padding: 20px; 
                overflow-y: auto; 
                background: #f8f9fa; 
                border-radius: 10px;
                margin-bottom: 20px;
            }
            .input-container { display: flex; gap: 10px; }
            .input-container input { 
                flex: 1; 
                padding: 15px; 
                border: 2px solid #dee2e6; 
                border-radius: 8px; 
                font-size: 16px; 
            }
            .input-container button { 
                padding: 15px 25px; 
                background: #007bff; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px;
            }
            .input-container button:hover { background: #0056b3; }
            .message { 
                margin: 15px 0; 
                padding: 12px 16px; 
                border-radius: 12px; 
                max-width: 80%; 
                animation: slideIn 0.3s ease;
            }
            .ai-message { 
                background: #e7f3ff; 
                border-left: 4px solid #007bff; 
            }
            .user-message { 
                background: #f0f8f0; 
                border-left: 4px solid #28a745; 
                margin-left: auto; 
                text-align: right; 
            }
            .quick-questions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 20px;
            }
            .quick-btn {
                padding: 8px 16px;
                background: #e9ecef;
                border: 1px solid #dee2e6;
                border-radius: 20px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s;
            }
            .quick-btn:hover {
                background: #007bff;
                color: white;
            }
            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 AI Mentor Assistant</h1>
                <p>Your intelligent coding companion</p>
                <div class="status">🟢 AI Service Active</div>
            </div>
            
            <div class="quick-questions">
                <div class="quick-btn" onclick="askQuestion('What is React and how do I get started?')">📚 React Basics</div>
                <div class="quick-btn" onclick="askQuestion('How do I debug JavaScript errors?')">🐛 Debug JS</div>
                <div class="quick-btn" onclick="askQuestion('Explain REST API best practices')">🔗 REST APIs</div>
                <div class="quick-btn" onclick="askQuestion('How to optimize database queries?')">💾 Database</div>
            </div>
            
            <div id="chatBox" class="chat-box">
                <div class="message ai-message">
                    👋 <strong>Hello!</strong> I'm your AI Mentor Assistant. Ask me anything about:
                    <br>• JavaScript, React, Python, Node.js
                    <br>• Debugging and error handling
                    <br>• API design and database optimization
                    <br>• Best practices and code review
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" id="questionInput" placeholder="Ask about coding, debugging, APIs, frameworks..." onkeypress="handleEnter(event)">
                <button onclick="sendQuestion()">Send</button>
            </div>
        </div>
        
        <script>
            function handleEnter(event) {
                if (event.key === 'Enter') sendQuestion();
            }
            
            function askQuestion(question) {
                document.getElementById('questionInput').value = question;
                sendQuestion();
            }
            
            async function sendQuestion() {
                const input = document.getElementById('questionInput');
                const chatBox = document.getElementById('chatBox');
                const question = input.value.trim();
                
                if (!question) return;
                
                // Add user message
                chatBox.innerHTML += `<div class="message user-message"><strong>You:</strong> ${question}</div>`;
                input.value = '';
                
                // Add loading message
                const loadingId = 'loading_' + Date.now();
                chatBox.innerHTML += `<div class="message ai-message" id="${loadingId}">🤔 <em>Thinking...</em></div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
                
                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question: question, context: 'web_interface' })
                    });
                    
                    const data = await response.json();
                    
                    // Remove loading message
                    document.getElementById(loadingId).remove();
                    
                    // Add AI response
                    const aiResponse = data.response || data.error || 'Sorry, I encountered an error.';
                    chatBox.innerHTML += `<div class="message ai-message"><strong>🤖 AI Mentor:</strong> ${aiResponse}</div>`;
                    chatBox.scrollTop = chatBox.scrollHeight;
                    
                } catch (error) {
                    document.getElementById(loadingId).remove();
                    chatBox.innerHTML += `<div class="message ai-message"><strong>❌ Error:</strong> ${error.message}</div>`;
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            }
            
            // Focus on input when page loads
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('questionInput').focus();
            });
        </script>
    </body>
    </html>
    '''

@app.route('/api/ask', methods=['POST'])
def ask_ai():
    """API endpoint to ask AI questions with senior-level interview support."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        context = data.get('context', 'web_interface')
        interview_mode = data.get('interview_mode', False)
        optimization = data.get('optimization', 'standard')
        interview_level = data.get('interview_level', '')
        requirements = data.get('requirements', {})
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        print(f"🎯 Received interview question: {question[:100]}...")
        print(f"📊 Interview level: {interview_level}")
        print(f"⚙️ Requirements: {requirements}")
        
        # Check if we should use personalized prompts
        final_question = question
        if interview_mode and PROFILE_MANAGER_AVAILABLE and profile_manager:
            try:
                # Generate personalized prompt based on user profile
                personalized_prompt = profile_manager.generate_personalized_prompt(question)
                final_question = personalized_prompt
                print(f"🧠 Using personalized prompt for senior-level interview question")
            except Exception as e:
                print(f"⚠️ Failed to generate personalized prompt: {e}")
                # Fall back to original question
                pass
        
        # Enhanced context for senior-level interview mode
        ai_context = {
            'type': context,
            'timestamp': datetime.now().isoformat(),
            'source': 'web_browser',
            'interview_mode': interview_mode,
            'optimization': optimization,
            'interview_level': interview_level,
            'requirements': requirements,
            'personalized': interview_mode and PROFILE_MANAGER_AVAILABLE,
            'temperature': data.get('temperature', 0.3 if 'IC6' in interview_level or 'IC7' in interview_level else 0.7)
        }
        
        # Add interview-specific context
        if interview_mode:
            if 'IC6' in interview_level or 'IC7' in interview_level or 'E5' in interview_level:
                ai_context.update({
                    'response_style': 'senior_engineer_comprehensive',
                    'format': 'senior_technical_interview',
                    'expertise_level': 'senior',
                    'optimization': optimization,
                    'context': 'senior_engineer_interview'
                })
            else:
                ai_context.update({
                    'response_style': 'concise_professional',
                    'format': 'interview_answer',
                    'optimization': optimization
                })
        
        # Use personalized prompt if profile manager is available
        if interview_mode and PROFILE_MANAGER_AVAILABLE:
            try:
                # Generate personalized prompt using user's profile
                personalized_prompt = profile_manager.generate_personalized_prompt(question)
                final_question = personalized_prompt
                ai_context['type'] = 'personalized_interview_response'
                logger.info(f"🎯 Using personalized prompt for senior interview question: {question[:50]}...")
                print(f"🎯 Generated personalized prompt (first 200 chars): {personalized_prompt[:200]}...")
            except Exception as e:
                logger.warning(f"⚠️ Could not generate personalized prompt: {e}")
                print(f"⚠️ Personalization failed: {e}")
        
        # Generate AI response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            ai_assistant._generate_ai_response(final_question, ai_context)
        )
        loop.close()
        
        # Post-process for interview mode
        if interview_mode:
            response = optimize_interview_response(response)
        
        return jsonify({
            'response': response,
            'answer': response,  # For backward compatibility
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'interview_mode': interview_mode
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def optimize_interview_response(response):
    """Optimize AI response for interview context."""
    if not response:
        return response
    
    # Remove AI-like phrases
    ai_phrases = [
        "As an AI", "I'm an AI", "As a language model", 
        "I don't have personal experience", "I cannot",
        "Here's what I think:", "Let me provide",
        "Based on my training"
    ]
    
    optimized = response
    for phrase in ai_phrases:
        optimized = optimized.replace(phrase, "")
    
    # Clean up and make more conversational
    optimized = optimized.strip()
    
    # Ensure it starts naturally
    if optimized.startswith("Based on"):
        optimized = optimized[9:].strip()
    
    return optimized

# Profile Management Endpoints
@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Upload and analyze resume"""
    if not PROFILE_MANAGER_AVAILABLE:
        return jsonify({'error': 'Profile manager not available'}), 503
    
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PDF, DOC, DOCX, or TXT'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Analyze resume
        analysis_result = profile_manager.analyze_resume(file_path, file.filename)
        
        # Clean up uploaded file (optional)
        # os.remove(file_path)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/save-profile', methods=['POST'])
def save_profile():
    """Save user profile data"""
    if not PROFILE_MANAGER_AVAILABLE:
        return jsonify({'error': 'Profile manager not available'}), 503
    
    try:
        profile_data = request.get_json()
        if not profile_data:
            return jsonify({'error': 'No profile data provided'}), 400
        
        success = profile_manager.save_profile(profile_data)
        if success:
            return jsonify({'success': True, 'message': 'Profile saved successfully'})
        else:
            return jsonify({'error': 'Failed to save profile'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500

@app.route('/api/get-profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    if not PROFILE_MANAGER_AVAILABLE:
        return jsonify({'error': 'Profile manager not available'}), 503
    
    try:
        profile = profile_manager.get_profile()
        return jsonify(profile)
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@app.route('/api/test-personalization', methods=['POST'])
def test_personalization():
    """Test personalized AI responses"""
    if not PROFILE_MANAGER_AVAILABLE:
        return jsonify({'error': 'Profile manager not available'}), 503
    
    try:
        data = request.get_json()
        test_questions = data.get('test_questions', [])
        
        if not test_questions:
            return jsonify({'error': 'No test questions provided'}), 400
        
        examples = profile_manager.test_personalization(test_questions)
        return jsonify({'examples': examples})
        
    except Exception as e:
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

@app.route('/profile')
def profile_page():
    """Redirect to profile manager page"""
    return redirect('/profile_manager.html')

@app.route('/profile_manager.html')
def profile_manager_page():
    """Serve the profile manager HTML page"""
    return send_from_directory('.', 'profile_manager.html')

@app.route('/api/set-interview-level', methods=['POST'])
def set_interview_level():
    """Set interview level for AI responses"""
    try:
        data = request.get_json()
        level = data.get('level', 'IC6')
        company = data.get('company', None)
        
        ai_assistant.set_interview_configuration(level, company)
        
        return jsonify({
            'success': True,
            'level': level,
            'company': company,
            'message': f'Interview level set to {level}' + (f' for {company}' if company else '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-interview-config', methods=['GET'])
def get_interview_config():
    """Get current interview configuration"""
    try:
        config = ai_assistant.get_interview_configuration()
        return jsonify({
            'success': True,
            **config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-company-questions', methods=['GET'])
def get_company_questions():
    """Get company-specific interview questions"""
    try:
        company = request.args.get('company')
        question_type = request.args.get('type')  # behavioral, technical, system_design
        
        if not company:
            return jsonify({'success': False, 'error': 'Company parameter required'}), 400
        
        # Get questions using the company knowledge base
        questions = ai_assistant.company_kb.get_company_questions(company, question_type) if ai_assistant.company_kb else []
        
        return jsonify({
            'success': True,
            'company': company,
            'question_type': question_type,
            'questions': questions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-interview-tips', methods=['GET'])
def get_interview_tips():
    """Get company-specific interview tips"""
    try:
        company = request.args.get('company')
        role_level = request.args.get('level', 'senior')
        
        if not company:
            return jsonify({'success': False, 'error': 'Company parameter required'}), 400
        
        tips = ai_assistant.company_kb.get_interview_tips(company, role_level) if ai_assistant.company_kb else {}
        
        return jsonify({
            'success': True,
            'company': company,
            'role_level': role_level,
            'tips': tips
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-similar-questions', methods=['POST'])
def search_similar_questions():
    """Search for similar interview questions"""
    try:
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({'success': False, 'error': 'Question parameter required'}), 400
        
        similar_questions = ai_assistant.get_similar_interview_questions(question)
        
        return jsonify({
            'success': True,
            'query': question,
            'similar_questions': similar_questions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'active',
        'model': Config.OPENAI_MODEL,
        'features': [
            'Real-time Q&A',
            'Coding assistance', 
            'Meeting support',
            'Context memory',
            'Resume Integration',
            'IC6/IC7 Level Responses'
        ]
    })

if __name__ == '__main__':
    print("🌐 Starting AI Mentor Assistant Web Interface...")
    print("📍 Open your browser to: http://localhost:8084")
    print("🤖 AI Assistant ready for live testing!")
    app.run(host='0.0.0.0', port=8084, debug=True)
