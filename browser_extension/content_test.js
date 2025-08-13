// AI Interview Assistant - Test Version with Always Visible Overlay
// This version shows the overlay immediately for testing purposes

console.log('🤖 AI Interview Assistant (TEST MODE) Loading...');

class AIInterviewAssistant {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.overlay = null;
        this.isStealthMode = false; // Disabled for testing
        this.questionTimeout = null;
        this.lastApiCall = 0;
        this.lastStatusMessage = '';
        this.isScreenSharing = false; // Track screen sharing
        this.overlayHidden = false; // Track if overlay is hidden for privacy
        
        console.log('🤖 AI Interview Assistant initialized in TEST MODE (overlay always visible)');
    }

    initialize() {
        console.log('🔧 Initializing AI Interview Assistant in TEST MODE...');
        
        // Create main overlay (always visible for testing)
        this.createOverlay();
        
        // Initialize speech recognition
        this.setupSpeechRecognition();
        
        // Check backend connection
        this.checkBackend();
        
        // Set up hotkeys
        this.setupHotkeys();
        
        // CRITICAL: Set up screen share detection for privacy
        this.setupScreenShareDetection();
        
        console.log('✅ AI Interview Assistant fully initialized in TEST MODE');
    }

    setupHotkeys() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+T to test functionality
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.testOverlay();
                console.log('🧪 Test function triggered');
            }
        });
    }

    testOverlay() {
        this.updateStatus('🧪 Test mode activated - overlay is working!');
        setTimeout(() => {
            this.updateStatus('✅ Ready for questions...');
        }, 3000);
    }

    createOverlay() {
        // Remove existing overlay
        const existing = document.getElementById('ai-assistant-overlay');
        if (existing) existing.remove();

        // Create overlay with maximum visibility
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        
        // Apply styles directly to ensure visibility
        this.overlay.style.cssText = `
            position: fixed !important;
            top: 20px !important;
            right: 20px !important;
            width: 380px !important;
            max-height: 90vh !important;
            background: rgba(0, 0, 0, 0.95) !important;
            color: #00ff00 !important;
            font-family: monospace !important;
            font-size: 12px !important;
            border: 2px solid #00ff00 !important;
            border-radius: 10px !important;
            z-index: 2147483647 !important;
            padding: 15px !important;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5) !important;
            overflow-y: auto !important;
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        `;
        
        this.overlay.innerHTML = `
            <div style="text-align: center; margin-bottom: 15px; color: #00ff00; font-weight: bold; font-size: 16px;">
                🤖 AI Interview Assistant (TEST MODE)
            </div>
            
            <div style="text-align: center; margin-bottom: 10px; font-size: 11px; color: #ff8c00; border: 1px solid #ff8c00; padding: 6px; border-radius: 5px; background: rgba(255, 140, 0, 0.1);">
                🧪 TEST MODE - Overlay Always Visible<br>
                <span style="color: #ff0000; font-size: 10px;">⚠️ PRIVACY: Hides automatically during screen share</span>
            </div>
            
            <div id="status" style="
                text-align: center;
                padding: 10px;
                background: rgba(0, 255, 0, 0.1);
                border: 1px solid #00ff00;
                border-radius: 5px;
                margin-bottom: 15px;
                font-size: 11px;
            ">
                🔧 Initializing...
            </div>
            
            <div style="margin-bottom: 15px;">
                <button id="register-btn" style="
                    width: 100%;
                    padding: 8px;
                    background: #00aaff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 8px;
                    font-size: 11px;
                ">🔑 Quick Register</button>
                
                <button id="test-btn" style="
                    width: 100%;
                    padding: 10px;
                    background: #00ff00;
                    color: black;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 10px;
                ">🧪 Test Overlay</button>
                
                <button id="toggle-listen" style="
                    width: 100%;
                    padding: 10px;
                    background: #ff8c00;
                    color: black;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                ">🎤 Start Listening</button>
            </div>
            
            <div id="answers" style="
                max-height: 300px;
                overflow-y: auto;
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid #333;
                border-radius: 5px;
                padding: 10px;
            ">
                <div style="color: #888; text-align: center; font-style: italic;">
                    No questions detected yet. Try speaking or use Ctrl+Shift+T to test.
                </div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(this.overlay);
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('✅ Test overlay created and added to page');
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
            
            const email = `demo${Date.now()}@aimentor.com`;
            const password = 'demo123456';
            
            const response = await fetch('http://localhost:8084/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('ai_mentor_token', data.token);
                this.updateStatus('✅ Account created! Try asking a question now.');
                
                // Show success message
                this.displayAnswer(`🎉 Account Created Successfully!\n\nEmail: ${email}\nSubscription: ${data.subscription}\n\nYou can now ask real AI questions! Try speaking or typing a question.`);
            } else {
                throw new Error('Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.updateStatus('❌ Registration failed - using demo mode');
        }
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
        // Simple question detection with debouncing
        if (transcript.includes('?') || 
            transcript.toLowerCase().includes('what') ||
            transcript.toLowerCase().includes('how') ||
            transcript.toLowerCase().includes('why') ||
            transcript.toLowerCase().includes('tell me')) {
            
            // Debounce to prevent multiple calls
            const now = Date.now();
            if (now - this.lastApiCall < 3000) { // Wait 3 seconds between questions
                console.log('⏳ Debouncing - waiting before next question');
                return;
            }
            
            this.lastApiCall = now;
            this.askAI(transcript);
        }
    }

    async askAI(question) {
        try {
            this.updateStatus('🤖 Generating AI response...');
            
            // Get stored token
            const token = localStorage.getItem('ai_mentor_token');
            
            // Connect to real AI backend with proper error handling
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                mode: 'cors',
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
                this.updateStatus('✅ AI response generated');
            } else if (response.status === 401) {
                // Handle authentication - show registration prompt
                const authResponse = `🔑 Authentication Required\n\nTo get real AI responses, click the "🔑 Quick Register" button above to create a free account.\n\nQuestion asked: "${question}"`;
                this.displayAnswer(authResponse);
                this.updateStatus('⚠️ Please register for AI responses');
            } else {
                const errorText = await response.text();
                throw new Error(`API error: ${response.status} - ${errorText}`);
            }
            
        } catch (error) {
            console.error('Error:', error);
            
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                // Network/CORS error
                const networkResponse = `🔌 Network Connection Issue\n\nQuestion: "${question}"\n\nCannot connect to AI backend. This might be a CORS issue or the backend is not running.\n\nTry: Check if backend is running on port 8084`;
                this.displayAnswer(networkResponse);
                this.updateStatus('❌ Network connection failed');
            } else {
                // Other error
                const fallbackResponse = `🔧 Technical Issue\n\nQuestion: "${question}"\n\nError: ${error.message}\n\nThis is a temporary issue with the AI backend.`;
                this.displayAnswer(fallbackResponse);
                this.updateStatus('❌ Backend error');
            }
        }
    }

    displayAnswer(answer) {
        const answersDiv = document.getElementById('answers');
        if (answersDiv) {
            const answerElement = document.createElement('div');
            answerElement.style.cssText = `
                margin-bottom: 15px;
                padding: 10px;
                background: rgba(0, 255, 0, 0.1);
                border-left: 3px solid #00ff00;
                border-radius: 3px;
            `;
            answerElement.innerHTML = `
                <div style="font-size: 10px; color: #888; margin-bottom: 5px;">
                    ${new Date().toLocaleTimeString()}
                </div>
                <div>${answer}</div>
            `;
            
            answersDiv.insertBefore(answerElement, answersDiv.firstChild);
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
                this.updateStatus('✅ Backend connected');
            } else {
                this.updateStatus('⚠️ Backend not responding');
            }
        } catch (error) {
            this.updateStatus('❌ Backend offline');
        }
    }

    setupScreenShareDetection() {
        // Monitor for screen sharing indicators
        const checkScreenShare = () => {
            // Check for Google Meet screen share indicators
            const screenShareButtons = document.querySelectorAll('[aria-label*="screen"], [aria-label*="Screen"], [data-tooltip*="screen"], [data-tooltip*="Screen"]');
            const isSharing = Array.from(screenShareButtons).some(btn => 
                btn.getAttribute('aria-pressed') === 'true' || 
                btn.classList.contains('active') ||
                btn.style.backgroundColor !== ''
            );
            
            // Also check for screen share text indicators
            const screenShareText = document.body.innerText.toLowerCase().includes('you are presenting') ||
                                  document.body.innerText.toLowerCase().includes('sharing your screen') ||
                                  document.querySelector('[data-is-presenting="true"]');
            
            const wasSharing = this.isScreenSharing;
            this.isScreenSharing = isSharing || screenShareText;
            
            if (this.isScreenSharing && !wasSharing) {
                console.log('🔒 Screen sharing detected - hiding overlay for privacy');
                this.hideForPrivacy();
            } else if (!this.isScreenSharing && wasSharing) {
                console.log('🔓 Screen sharing stopped - showing overlay');
                this.showAfterPrivacy();
            }
        };
        
        // Check every 1 second for screen sharing changes
        setInterval(checkScreenShare, 1000);
        
        // Also check on DOM changes
        const observer = new MutationObserver(checkScreenShare);
        observer.observe(document.body, { childList: true, subtree: true, attributes: true });
    }

    hideForPrivacy() {
        if (this.overlay && !this.overlayHidden) {
            console.log('🫥 PRIVACY MODE: Hiding overlay from screen share');
            this.overlay.style.display = 'none';
            this.overlayHidden = true;
            
            // Show a minimal notification that doesn't appear in screen share
            this.showPrivacyNotification();
        }
    }

    showAfterPrivacy() {
        if (this.overlay && this.overlayHidden) {
            console.log('👁️ PRIVACY MODE OFF: Showing overlay');
            this.overlay.style.display = 'block';
            this.overlayHidden = false;
            
            // Remove privacy notification
            const notification = document.getElementById('privacy-notification');
            if (notification) notification.remove();
        }
    }

    showPrivacyNotification() {
        // Create a very subtle notification that won't appear in screen capture
        const notification = document.createElement('div');
        notification.id = 'privacy-notification';
        notification.style.cssText = `
            position: fixed !important;
            bottom: 5px !important;
            right: 5px !important;
            width: 20px !important;
            height: 20px !important;
            background: #333 !important;
            border-radius: 50% !important;
            z-index: 999999 !important;
            opacity: 0.3 !important;
            pointer-events: none !important;
        `;
        document.body.appendChild(notification);
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
