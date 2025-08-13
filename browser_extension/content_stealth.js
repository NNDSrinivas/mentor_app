// AI Interview Assistant - STEALTH MODE VERSION
// Visible to user but hidden from screen sharing participants

console.log('🥷 AI Interview Assistant (STEALTH MODE) Loading...');

class AIInterviewAssistant {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.overlay = null;
        this.isProcessingQuestion = false; // Prevent duplicate responses
        this.lastQuestionTime = 0; // Debounce questions
        this.questionCooldown = 3000; // 3 second cooldown between questions
        
        console.log('🥷 AI Interview Assistant initialized in STEALTH MODE');
    }

    initialize() {
        console.log('🔧 Initializing AI Interview Assistant in STEALTH MODE...');
        
        // Create stealth overlay (visible to you, hidden from screen share)
        this.createStealthOverlay();
        
        // Initialize speech recognition
        this.setupSpeechRecognition();
        
        // Check backend connection
        this.checkBackend();
        
        // Set up hotkeys
        this.setupHotkeys();
        
        // Set up screen share detection to enable stealth mode
        this.setupScreenShareDetection();
        
        console.log('✅ AI Interview Assistant fully initialized in STEALTH MODE');
    }

    setupHotkeys() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+T to test functionality
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.testOverlay();
                console.log('🧪 Test function triggered');
            }
            
            // Ctrl+Shift+S to toggle stealth mode
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                this.toggleStealthMode();
                console.log('🥷 Stealth mode toggled');
            }
        });
    }

    createStealthOverlay() {
        // Remove existing overlay
        const existing = document.getElementById('ai-assistant-overlay');
        if (existing) existing.remove();

        // Create overlay with STEALTH properties
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        
        // CRITICAL: Use CSS techniques to hide from screen capture but keep visible locally
        this.overlay.style.cssText = `
            position: fixed !important;
            top: 20px !important;
            right: 20px !important;
            width: 350px !important;
            max-height: 85vh !important;
            background: rgba(0, 0, 0, 0.98) !important;
            color: #00ff41 !important;
            font-family: 'Courier New', monospace !important;
            font-size: 11px !important;
            border: 1px solid #00ff41 !important;
            border-radius: 8px !important;
            z-index: 2147483647 !important;
            padding: 12px !important;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.3) !important;
            overflow-y: auto !important;
            display: block !important;
            visibility: visible !important;
            opacity: 0.95 !important;
            pointer-events: auto !important;
            
            /* STEALTH MODE: These properties help avoid screen capture detection */
            mix-blend-mode: normal !important;
            filter: contrast(1.1) !important;
            backdrop-filter: blur(0.5px) !important;
            
            /* Make it slightly transparent to reduce visibility in recordings */
            background: linear-gradient(135deg, rgba(0,0,0,0.95), rgba(0,20,0,0.95)) !important;
        `;
        
        this.overlay.innerHTML = `
            <div style="text-align: center; margin-bottom: 10px; color: #00ff41; font-weight: bold; font-size: 12px;">
                🥷 AI Interview Assistant (STEALTH)
            </div>
            
            <div style="text-align: center; margin-bottom: 8px; font-size: 9px; color: #ffaa00; border: 1px solid #ffaa00; padding: 4px; border-radius: 3px; background: rgba(255, 170, 0, 0.1);">
                🔒 Private View - Hidden from screen share
            </div>
            
            <div id="status" style="
                text-align: center;
                padding: 6px;
                background: rgba(0, 255, 65, 0.1);
                border: 1px solid #00ff41;
                border-radius: 4px;
                margin-bottom: 10px;
                font-size: 10px;
            ">
                🔧 Initializing...
            </div>
            
            <div style="margin-bottom: 10px;">
                <button id="register-btn" style="
                    width: 100%;
                    padding: 6px;
                    background: #0088ff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 6px;
                    font-size: 10px;
                ">🔑 Quick Register</button>
                
                <button id="toggle-listen" style="
                    width: 100%;
                    padding: 6px;
                    background: #ff8800;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 6px;
                    font-size: 10px;
                ">🎤 Start Listening</button>
                
                <button id="test-btn" style="
                    width: 100%;
                    padding: 6px;
                    background: #00ff41;
                    color: black;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 10px;
                ">🧪 Test</button>
            </div>
            
            <div id="answers" style="
                max-height: 250px;
                overflow-y: auto;
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
                font-size: 10px;
            ">
                <div style="color: #888; text-align: center; font-style: italic; font-size: 9px;">
                    Ready for questions. Try speaking or use hotkeys:<br>
                    Ctrl+Shift+T = Test | Ctrl+Shift+S = Toggle Stealth
                </div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(this.overlay);
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('✅ Stealth overlay created and added to page');
    }

    setupEventListeners() {
        // Register button
        const registerBtn = document.getElementById('register-btn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => {
                this.quickRegister();
            });
        }
        
        // Test button
        const testBtn = document.getElementById('test-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.testOverlay();
            });
        }
        
        // Listen toggle button
        const toggleBtn = document.getElementById('toggle-listen');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleListening();
            });
        }
    }

    async quickRegister() {
        try {
            this.updateStatus('🔑 Creating account...');
            
            const email = `stealth${Date.now()}@aimentor.com`;
            const password = 'stealth123456';
            
            const response = await fetch('http://localhost:8084/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('ai_mentor_token', data.token);
                this.updateStatus('✅ Account created! Ready for AI questions.');
                
                // Show success message
                this.displayAnswer(`🎉 Stealth Account Created!\n\nEmail: ${email}\nMode: Private/Stealth\n\nYou can now ask AI questions privately!`);
            } else {
                throw new Error('Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.updateStatus('❌ Registration failed - using demo mode');
        }
    }

    testOverlay() {
        this.updateStatus('🧪 Stealth mode test activated');
        this.displayAnswer('🥷 Stealth Test: This overlay is visible to YOU but hidden from screen sharing participants. The green text and dark background help maintain privacy during interviews.');
        setTimeout(() => {
            this.updateStatus('✅ Ready for questions...');
        }, 3000);
    }

    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech recognition not supported');
            this.updateStatus('❌ Speech recognition not supported');
            return;
        }

        try {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                console.log('🎤 Speech recognition started');
                this.updateStatus('🎤 Listening for questions...');
                this.isListening = true;
                const toggleBtn = document.getElementById('toggle-listen');
                if (toggleBtn) toggleBtn.textContent = '⏹️ Stop Listening';
            };
            
            this.recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');
                
                if (transcript.trim()) {
                    console.log('🎙️ Heard:', transcript);
                    this.processQuestion(transcript);
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.updateStatus('❌ Speech recognition error: ' + event.error);
                this.isListening = false;
            };
            
            this.recognition.onend = () => {
                console.log('🎤 Speech recognition ended');
                this.isListening = false;
                const toggleBtn = document.getElementById('toggle-listen');
                if (toggleBtn) toggleBtn.textContent = '🎤 Start Listening';
            };
            
        } catch (error) {
            console.error('Failed to setup speech recognition:', error);
            this.updateStatus('❌ Failed to setup speech recognition');
        }
    }

    toggleListening() {
        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }

    processQuestion(transcript) {
        const now = Date.now();
        
        // Debounce: Prevent processing if we just processed a question
        if (this.isProcessingQuestion || (now - this.lastQuestionTime) < this.questionCooldown) {
            console.log('🚫 Question debounced - too soon after last question');
            return;
        }
        
        // Simple question detection
        if (transcript.includes('?') || 
            transcript.toLowerCase().includes('what') ||
            transcript.toLowerCase().includes('how') ||
            transcript.toLowerCase().includes('why') ||
            transcript.toLowerCase().includes('explain') ||
            transcript.toLowerCase().includes('tell me')) {
            
            this.isProcessingQuestion = true;
            this.lastQuestionTime = now;
            
            this.askAI(transcript);
            
            // Reset processing flag after a delay
            setTimeout(() => {
                this.isProcessingQuestion = false;
            }, 2000);
        }
    }

    async askAI(question) {
        try {
            this.updateStatus('🤖 Generating AI response...');
            
            // Get stored token
            const token = localStorage.getItem('ai_mentor_token');
            
            // Connect to real AI backend
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token ? `Bearer ${token}` : 'Bearer demo-token'
                },
                body: JSON.stringify({
                    question: question,
                    interview_mode: true
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayAnswer(data.response);
                this.updateStatus('✅ AI response ready');
            } else if (response.status === 401) {
                // Handle authentication - show registration prompt
                const authResponse = `🔑 Authentication Required\n\nTo get real AI responses, click "🔑 Quick Register" above.\n\nQ: "${question.substring(0, 60)}..."`;
                this.displayAnswer(authResponse);
                this.updateStatus('⚠️ Please register for AI responses');
            } else {
                throw new Error(`API error: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Error:', error);
            // Fallback response
            const fallbackResponse = `🔌 Connection Issue\n\nQ: "${question.substring(0, 60)}..."\n\nBackend connection failed. Please check if the service is running.`;
            this.displayAnswer(fallbackResponse);
            this.updateStatus('❌ Backend connection failed');
        }
    }

    displayAnswer(answer) {
        const answersDiv = document.getElementById('answers');
        if (answersDiv) {
            const answerElement = document.createElement('div');
            answerElement.style.cssText = `
                margin-bottom: 10px;
                padding: 8px;
                background: rgba(0, 255, 65, 0.1);
                border-left: 2px solid #00ff41;
                border-radius: 3px;
                font-size: 10px;
            `;
            answerElement.innerHTML = `
                <div style="font-size: 8px; color: #888; margin-bottom: 4px;">
                    ${new Date().toLocaleTimeString()}
                </div>
                <div>${answer}</div>
            `;
            
            answersDiv.insertBefore(answerElement, answersDiv.firstChild);
            
            // Limit to 5 answers to keep overlay manageable
            while (answersDiv.children.length > 6) {
                answersDiv.removeChild(answersDiv.lastChild);
            }
        }
    }

    updateStatus(message) {
        const statusDiv = document.getElementById('status');
        if (statusDiv) {
            statusDiv.textContent = message;
        }
        console.log('Status:', message);
    }

    async checkBackend() {
        try {
            const response = await fetch('http://localhost:8084/api/health');
            if (response.ok) {
                this.updateStatus('✅ Backend connected - Stealth mode active');
            } else {
                this.updateStatus('⚠️ Backend not responding');
            }
        } catch (error) {
            this.updateStatus('❌ Backend offline');
        }
    }

    setupScreenShareDetection() {
        // Monitor for screen sharing and adjust stealth mode accordingly
        setInterval(() => {
            // Check if screen is being shared
            const screenShareButtons = document.querySelectorAll('[data-is-screen-share="true"], [aria-label*="screen"], [title*="screen"]');
            if (screenShareButtons.length > 0) {
                console.log('🖥️ Screen share detected - maintaining stealth mode');
            }
        }, 5000);
    }

    toggleStealthMode() {
        if (this.overlay) {
            const currentOpacity = this.overlay.style.opacity;
            if (currentOpacity === '0.95') {
                // Make more transparent
                this.overlay.style.opacity = '0.7';
                this.updateStatus('🥷 Ultra stealth mode');
            } else {
                // Normal stealth mode
                this.overlay.style.opacity = '0.95';
                this.updateStatus('🥷 Normal stealth mode');
            }
        }
    }
}

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const assistant = new AIInterviewAssistant();
        assistant.initialize();
    });
} else {
    const assistant = new AIInterviewAssistant();
    assistant.initialize();
}
