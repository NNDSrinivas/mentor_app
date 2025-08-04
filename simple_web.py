#!/usr/bin/env python3
"""
Simple AI Mentor Web Interface for Testing
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from datetime import datetime
from app.ai_assistant import AIAssistant
from app.config import Config
import base64
import io

app = Flask(__name__)
CORS(app)

ai_assistant = AIAssistant()

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
    """API endpoint to ask AI questions."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        context = data.get('context', 'web_interface')
        interview_mode = data.get('interview_mode', False)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Generate AI response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if interview_mode:
            # Use interview-specific response that includes resume context
            response = loop.run_until_complete(
                ai_assistant._generate_interview_response(question)
            )
        else:
            # Use general response
            response = loop.run_until_complete(
                ai_assistant._generate_ai_response(question, {
                    'type': context,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'web_browser'
                })
            )
        
        loop.close()
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'interview_mode': interview_mode,
            'has_resume': ai_assistant.has_resume_context()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resume', methods=['POST'])
def upload_resume():
    """Upload and store resume for personalized responses."""
    try:
        data = request.get_json()
        resume_text = data.get('resume_text', '')
        
        if not resume_text.strip():
            return jsonify({'error': 'Resume text is required'}), 400
        
        # Store resume in AI assistant for context
        ai_assistant.set_resume_context(resume_text)
        
        return jsonify({
            'status': 'success',
            'message': 'Resume uploaded successfully',
            'resume_length': len(resume_text)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resume', methods=['GET'])
def get_resume_status():
    """Get current resume status."""
    return jsonify({
        'has_resume': ai_assistant.has_resume_context(),
        'resume_length': ai_assistant.get_resume_length() if ai_assistant.has_resume_context() else 0
    })

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
            'Resume-based responses'
        ]
    })

if __name__ == '__main__':
    print("🌐 Starting AI Mentor Assistant Web Interface...")
    print("📍 Open your browser to: http://localhost:8084")
    print("🤖 AI Assistant ready for live testing!")
    app.run(host='0.0.0.0', port=8084, debug=True)
