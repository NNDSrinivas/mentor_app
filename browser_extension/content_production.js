// Production AI Interview Assistant - Chrome Extension
// Handles authentication and calls production API

class ProductionAIAssistant {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.overlay = null;
        this.isStealthMode = true;
        this.lastApiCall = 0;
        this.userToken = null;
        this.userInfo = null;
        
        // Production API configuration
        this.API_BASE_URL = 'https://your-production-domain.com/api'; // UPDATE THIS
        // For testing locally, use: 'http://localhost:8084/api'
        
        console.log('🤖 Production AI Assistant initialized');
    }

    async initialize() {
        console.log('🔧 Initializing Production AI Assistant...');
        
        // Check if user is authenticated
        await this.loadUserAuth();
        
        // Initialize speech recognition
        this.initializeSpeechRecognition();
        
        // Create main overlay (initially hidden for privacy)
        this.createOverlay();
        
        // Activate stealth mode by default
        this.activateFullStealth();
        
        // Check backend connection and auth status
        await this.checkBackendAndAuth();
        
        // Set up hotkeys
        this.setupHotkeys();
        
        // Set up screen sharing detection
        this.setupEnhancedScreenShareDetection();
        
        console.log('✅ Production AI Assistant fully initialized');
    }

    async loadUserAuth() {
        try {
            // Load user token from Chrome storage
            const result = await chrome.storage.local.get(['userToken', 'userInfo']);
            this.userToken = result.userToken;
            this.userInfo = result.userInfo;
            
            if (this.userToken) {
                console.log('✅ User authenticated:', this.userInfo?.email);
            } else {
                console.log('❌ User not authenticated');
            }
        } catch (error) {
            console.error('Failed to load user auth:', error);
        }
    }

    async saveUserAuth(token, userInfo) {
        try {
            await chrome.storage.local.set({
                userToken: token,
                userInfo: userInfo
            });
            this.userToken = token;
            this.userInfo = userInfo;
            console.log('✅ User auth saved');
        } catch (error) {
            console.error('Failed to save user auth:', error);
        }
    }

    async clearUserAuth() {
        try {
            await chrome.storage.local.remove(['userToken', 'userInfo']);
            this.userToken = null;
            this.userInfo = null;
            console.log('✅ User auth cleared');
        } catch (error) {
            console.error('Failed to clear user auth:', error);
        }
    }

    async checkBackendAndAuth() {
        try {
            // Check backend health
            const healthResponse = await fetch(`${this.API_BASE_URL}/health`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (healthResponse.ok) {
                this.updateStatus('Backend connected', 'success');
                
                // If we have a token, verify it's still valid
                if (this.userToken) {
                    await this.verifyToken();
                } else {
                    this.updateStatus('Please login to use AI features', 'warning');
                }
            } else {
                this.updateStatus('Backend unavailable', 'error');
            }
        } catch (error) {
            console.error('Backend check failed:', error);
            this.updateStatus('Backend connection failed', 'error');
        }
    }

    async verifyToken() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/usage`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const usageData = await response.json();
                this.updateStatus(`${usageData.subscription_tier} plan: ${usageData.remaining}/${usageData.monthly_limit} remaining`, 'success');
            } else if (response.status === 401) {
                // Token expired or invalid
                await this.clearUserAuth();
                this.updateStatus('Session expired - please login', 'warning');
            } else {
                this.updateStatus('Auth verification failed', 'error');
            }
        } catch (error) {
            console.error('Token verification failed:', error);
            this.updateStatus('Auth check failed', 'error');
        }
    }

    async askQuestion(question, isInterviewMode = false) {
        if (!this.userToken) {
            this.updateStatus('Please login to ask questions', 'warning');
            this.displayAnswer('Please login first to use AI features. Click the extension icon to login or signup.');
            return;
        }

        const now = Date.now();
        
        // Rate limiting
        if (now - this.lastApiCall < 2000) {
            console.log('⏱️ Rate limited - waiting...');
            return;
        }
        this.lastApiCall = now;

        if (!question || question.trim().length === 0) {
            console.log('❌ Empty question provided');
            return;
        }

        this.updateStatus('AI thinking...', 'processing');

        try {
            const requestBody = {
                question: question.trim(),
                interview_mode: isInterviewMode
            };

            const response = await fetch(`${this.API_BASE_URL}/ask`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                const data = await response.json();
                this.displayAnswer(data.answer);
                this.updateStatus('AI response ready', 'success');
                
                // Update usage information if provided
                if (data.subscription_tier) {
                    console.log(`Usage: ${data.subscription_tier} plan`);
                }
            } else if (response.status === 401) {
                // Token expired
                await this.clearUserAuth();
                this.updateStatus('Session expired - please login', 'warning');
                this.displayAnswer('Your session has expired. Please login again to continue using AI features.');
            } else if (response.status === 429) {
                // Usage limit exceeded
                const errorData = await response.json();
                this.updateStatus('Usage limit exceeded', 'error');
                this.displayAnswer(`You've reached your monthly limit of ${errorData.limit} questions. Please upgrade your plan to continue.`);
            } else {
                const errorData = await response.json();
                this.updateStatus('AI request failed', 'error');
                this.displayAnswer(`Sorry, I couldn't process your question: ${errorData.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('AI request failed:', error);
            this.updateStatus('Connection failed', 'error');
            this.displayAnswer('Sorry, I couldn\'t connect to the AI service. Please check your internet connection and try again.');
        }
    }

    async uploadResume(resumeText) {
        if (!this.userToken) {
            this.updateStatus('Please login to upload resume', 'warning');
            return false;
        }

        try {
            const response = await fetch(`${this.API_BASE_URL}/resume`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ resume_text: resumeText })
            });

            if (response.ok) {
                this.updateStatus('Resume uploaded successfully', 'success');
                return true;
            } else if (response.status === 401) {
                await this.clearUserAuth();
                this.updateStatus('Session expired - please login', 'warning');
                return false;
            } else {
                const errorData = await response.json();
                this.updateStatus('Resume upload failed', 'error');
                console.error('Resume upload error:', errorData.error);
                return false;
            }
        } catch (error) {
            console.error('Resume upload failed:', error);
            this.updateStatus('Resume upload failed', 'error');
            return false;
        }
    }

    initializeSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            console.warn('Speech recognition not supported');
            return;
        }

        this.recognition = new webkitSpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                }
            }

            if (finalTranscript) {
                console.log('🎤 Speech recognized:', finalTranscript);
                this.askQuestion(finalTranscript, true); // Interview mode for speech
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.updateStatus(`Speech error: ${event.error}`, 'error');
        };

        this.recognition.onend = () => {
            if (this.isListening) {
                this.recognition.start(); // Restart if still supposed to be listening
            }
        };
    }

    startListening() {
        if (!this.userToken) {
            this.updateStatus('Please login to use speech recognition', 'warning');
            return;
        }

        if (!this.recognition) {
            this.updateStatus('Speech recognition not available', 'error');
            return;
        }

        this.isListening = true;
        this.recognition.start();
        this.updateStatus('Listening...', 'processing');
        console.log('🎤 Started listening');
    }

    stopListening() {
        this.isListening = false;
        if (this.recognition) {
            this.recognition.stop();
        }
        this.updateStatus('Stopped listening', 'idle');
        console.log('🎤 Stopped listening');
    }

    createOverlay() {
        if (this.overlay) return;

        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        this.overlay.innerHTML = `
            <div id="ai-assistant-content">
                <div id="ai-assistant-header">
                    <span id="ai-assistant-title">🤖 AI Mentor</span>
                    <div id="ai-assistant-controls">
                        <button id="ai-stealth-toggle" title="Toggle Stealth Mode">👁️</button>
                        <button id="ai-mic-toggle" title="Toggle Microphone">🎤</button>
                        <button id="ai-close" title="Close">✕</button>
                    </div>
                </div>
                <div id="ai-assistant-status">Ready</div>
                <div id="ai-assistant-input-area">
                    <input type="text" id="ai-question-input" placeholder="Ask a question..." />
                    <button id="ai-ask-btn">Ask</button>
                </div>
                <div id="ai-assistant-response" style="display: none;"></div>
            </div>
        `;

        // Add styles
        const styles = `
            #ai-assistant-overlay {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 350px;
                background: rgba(0, 0, 0, 0.95);
                border: 1px solid #333;
                border-radius: 10px;
                z-index: 999999;
                font-family: Arial, sans-serif;
                color: white;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                backdrop-filter: blur(5px);
            }

            #ai-assistant-content {
                padding: 15px;
            }

            #ai-assistant-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
                border-bottom: 1px solid #333;
                padding-bottom: 10px;
            }

            #ai-assistant-title {
                font-weight: bold;
                font-size: 14px;
            }

            #ai-assistant-controls button {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                margin-left: 5px;
                padding: 5px;
                border-radius: 3px;
                font-size: 12px;
            }

            #ai-assistant-controls button:hover {
                background: rgba(255,255,255,0.1);
            }

            #ai-assistant-status {
                font-size: 12px;
                color: #888;
                margin-bottom: 10px;
                text-align: center;
            }

            #ai-assistant-input-area {
                display: flex;
                gap: 5px;
                margin-bottom: 10px;
            }

            #ai-question-input {
                flex: 1;
                padding: 8px;
                border: 1px solid #333;
                border-radius: 5px;
                background: rgba(255,255,255,0.1);
                color: white;
                font-size: 12px;
            }

            #ai-ask-btn {
                padding: 8px 12px;
                background: #007bff;
                border: none;
                border-radius: 5px;
                color: white;
                cursor: pointer;
                font-size: 12px;
            }

            #ai-ask-btn:hover {
                background: #0056b3;
            }

            #ai-assistant-response {
                max-height: 200px;
                overflow-y: auto;
                padding: 10px;
                background: rgba(255,255,255,0.05);
                border-radius: 5px;
                font-size: 12px;
                line-height: 1.4;
                white-space: pre-wrap;
                word-wrap: break-word;
            }

            .stealth-hidden {
                display: none !important;
            }
        `;

        const styleElement = document.createElement('style');
        styleElement.textContent = styles;
        document.head.appendChild(styleElement);

        document.body.appendChild(this.overlay);

        // Add event listeners
        this.setupOverlayEventListeners();
    }

    setupOverlayEventListeners() {
        const questionInput = document.getElementById('ai-question-input');
        const askBtn = document.getElementById('ai-ask-btn');
        const micToggle = document.getElementById('ai-mic-toggle');
        const stealthToggle = document.getElementById('ai-stealth-toggle');
        const closeBtn = document.getElementById('ai-close');

        if (questionInput && askBtn) {
            const handleAsk = () => {
                const question = questionInput.value.trim();
                if (question) {
                    this.askQuestion(question, false);
                    questionInput.value = '';
                }
            };

            askBtn.addEventListener('click', handleAsk);
            questionInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handleAsk();
                }
            });
        }

        if (micToggle) {
            micToggle.addEventListener('click', () => {
                if (this.isListening) {
                    this.stopListening();
                } else {
                    this.startListening();
                }
            });
        }

        if (stealthToggle) {
            stealthToggle.addEventListener('click', () => {
                this.toggleStealthMode();
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideOverlay();
            });
        }
    }

    displayAnswer(answer) {
        const responseDiv = document.getElementById('ai-assistant-response');
        if (responseDiv) {
            responseDiv.textContent = answer;
            responseDiv.style.display = 'block';
        }
    }

    updateStatus(message, type = 'idle') {
        const statusDiv = document.getElementById('ai-assistant-status');
        if (statusDiv) {
            statusDiv.textContent = message;
            
            // Update color based on type
            const colors = {
                'success': '#28a745',
                'error': '#dc3545',
                'warning': '#ffc107',
                'processing': '#17a2b8',
                'idle': '#888'
            };
            
            statusDiv.style.color = colors[type] || colors.idle;
        }
    }

    toggleStealthMode() {
        this.isStealthMode = !this.isStealthMode;
        
        if (this.isStealthMode) {
            this.activateFullStealth();
        } else {
            this.deactivateFullStealth();
        }
    }

    activateFullStealth() {
        this.isStealthMode = true;
        if (this.overlay) {
            this.overlay.classList.add('stealth-hidden');
        }
        console.log('🕶️ Full stealth mode activated');
    }

    deactivateFullStealth() {
        this.isStealthMode = false;
        if (this.overlay) {
            this.overlay.classList.remove('stealth-hidden');
        }
        console.log('👁️ Stealth mode deactivated');
    }

    hideOverlay() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
        }
    }

    showOverlay() {
        if (this.overlay) {
            this.overlay.style.display = 'block';
        }
    }

    setupHotkeys() {
        document.addEventListener('keydown', (event) => {
            // Ctrl+Shift+A to toggle assistant
            if (event.ctrlKey && event.shiftKey && event.key === 'A') {
                event.preventDefault();
                this.toggleStealthMode();
            }
            
            // Ctrl+Shift+M to toggle microphone
            if (event.ctrlKey && event.shiftKey && event.key === 'M') {
                event.preventDefault();
                if (this.isListening) {
                    this.stopListening();
                } else {
                    this.startListening();
                }
            }
        });
    }

    setupEnhancedScreenShareDetection() {
        // Screen sharing detection logic
        // This is a simplified version - you may need more sophisticated detection
        setInterval(() => {
            // Check for screen sharing indicators
            const screenShareIndicators = document.querySelectorAll('[data-screen-share], .screen-share, .screenshare');
            if (screenShareIndicators.length > 0) {
                if (!this.isStealthMode) {
                    console.log('🖥️ Screen sharing detected - activating stealth mode');
                    this.activateFullStealth();
                }
            }
        }, 1000);
    }
}

// Message handling for popup communication
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getAuthStatus') {
        sendResponse({
            isAuthenticated: assistant.userToken !== null,
            userInfo: assistant.userInfo
        });
    } else if (request.action === 'logout') {
        assistant.clearUserAuth();
        assistant.updateStatus('Logged out', 'idle');
        sendResponse({ success: true });
    } else if (request.action === 'setAuth') {
        assistant.saveUserAuth(request.token, request.userInfo);
        assistant.updateStatus(`Welcome ${request.userInfo.email}`, 'success');
        sendResponse({ success: true });
    }
});

// Initialize the assistant
const assistant = new ProductionAIAssistant();

// Wait for page load then initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => assistant.initialize());
} else {
    assistant.initialize();
}

console.log('🚀 Production AI Interview Assistant loaded');
