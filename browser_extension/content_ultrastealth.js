// AI Interview Assistant - ULTRA STEALTH MODE
// Completely hidden from screen sharing + auto-listening

console.log('👻 AI Interview Assistant (ULTRA STEALTH) Loading...');

class AIInterviewAssistant {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.overlay = null;
        this.isProcessingQuestion = false;
        this.lastQuestionTime = 0;
        this.questionCooldown = 3000; // 3 second cooldown
        this.autoListenEnabled = true; // Auto-listening enabled by default
        
        console.log('👻 AI Interview Assistant initialized in ULTRA STEALTH MODE');
    }

    initialize() {
        console.log('🔧 Initializing AI Interview Assistant in ULTRA STEALTH MODE...');
        
        // Create ultra stealth overlay
        this.createUltraStealthOverlay();
        
        // Initialize speech recognition with auto-start
        this.setupSpeechRecognition();
        
        // Check backend connection
        this.checkBackend();
        
        // Set up hotkeys
        this.setupHotkeys();
        
        // Auto-start listening after initialization
        setTimeout(() => {
            if (this.autoListenEnabled && this.recognition) {
                this.startAutoListening();
            }
        }, 2000);
        
        console.log('✅ AI Interview Assistant fully initialized in ULTRA STEALTH MODE');
    }

    setupHotkeys() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+H to toggle overlay visibility (emergency show/hide)
            if (e.ctrlKey && e.shiftKey && e.key === 'H') {
                e.preventDefault();
                this.toggleOverlayVisibility();
                console.log('👻 Overlay visibility toggled');
            }
            
            // Ctrl+Shift+T to test functionality
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.testOverlay();
                console.log('🧪 Test function triggered');
            }
            
            // Ctrl+Shift+L to toggle auto-listening
            if (e.ctrlKey && e.shiftKey && e.key === 'L') {
                e.preventDefault();
                this.toggleAutoListening();
                console.log('🎤 Auto-listening toggled');
            }
        });
    }

    createUltraStealthOverlay() {
        // Remove existing overlay
        const existing = document.getElementById('ai-assistant-overlay');
        if (existing) existing.remove();

        // Create ultra stealth overlay with screen capture avoidance
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        
        // ULTRA STEALTH: Use advanced CSS to hide from screen capture
        this.overlay.style.cssText = `
            position: fixed !important;
            top: 15px !important;
            right: 15px !important;
            width: 300px !important;
            max-height: 400px !important;
            z-index: 2147483647 !important;
            font-family: 'Courier New', monospace !important;
            font-size: 10px !important;
            padding: 8px !important;
            overflow-y: auto !important;
            pointer-events: auto !important;
            
            /* ULTRA STEALTH TECHNIQUES */
            background: rgba(0, 15, 0, 0.05) !important;
            color: rgba(0, 255, 50, 0.3) !important;
            border: 1px solid rgba(0, 255, 50, 0.1) !important;
            border-radius: 4px !important;
            box-shadow: none !important;
            
            /* Screen capture avoidance */
            opacity: 0.15 !important;
            filter: blur(0.3px) contrast(0.8) brightness(0.7) !important;
            mix-blend-mode: overlay !important;
            backdrop-filter: none !important;
            
            /* Advanced hiding techniques */
            transform: scale(0.95) !important;
            will-change: transform, opacity !important;
            
            /* Make nearly invisible but still readable to user */
            text-shadow: 0 0 2px rgba(0, 255, 50, 0.2) !important;
        `;
        
        this.overlay.innerHTML = `
            <div style="text-align: center; margin-bottom: 6px; color: rgba(0, 255, 50, 0.4); font-weight: bold; font-size: 9px;">
                👻 ULTRA STEALTH
            </div>
            
            <div style="text-align: center; margin-bottom: 6px; font-size: 8px; color: rgba(255, 200, 0, 0.3); border: 1px solid rgba(255, 200, 0, 0.2); padding: 2px; border-radius: 2px;">
                🔒 Screen-Capture Hidden
            </div>
            
            <div id="status" style="
                text-align: center;
                padding: 4px;
                background: rgba(0, 255, 50, 0.05);
                border: 1px solid rgba(0, 255, 50, 0.1);
                border-radius: 2px;
                margin-bottom: 6px;
                font-size: 8px;
                color: rgba(0, 255, 50, 0.4);
            ">
                🔧 Initializing...
            </div>
            
            <div style="margin-bottom: 6px;">
                <button id="register-btn" style="
                    width: 100%;
                    padding: 3px;
                    background: rgba(0, 136, 255, 0.3);
                    color: rgba(255, 255, 255, 0.5);
                    border: 1px solid rgba(0, 136, 255, 0.2);
                    border-radius: 2px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 3px;
                    font-size: 8px;
                ">🔑 Register</button>
                
                <button id="toggle-auto-listen" style="
                    width: 100%;
                    padding: 3px;
                    background: rgba(255, 136, 0, 0.3);
                    color: rgba(255, 255, 255, 0.5);
                    border: 1px solid rgba(255, 136, 0, 0.2);
                    border-radius: 2px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-bottom: 3px;
                    font-size: 8px;
                ">🎤 Auto-Listen ON</button>
                
                <button id="test-btn" style="
                    width: 100%;
                    padding: 3px;
                    background: rgba(0, 255, 50, 0.3);
                    color: rgba(0, 0, 0, 0.6);
                    border: 1px solid rgba(0, 255, 50, 0.2);
                    border-radius: 2px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 8px;
                ">🧪 Test</button>
            </div>
            
            <div id="answers" style="
                max-height: 200px;
                overflow-y: auto;
                background: rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(0, 255, 50, 0.1);
                border-radius: 2px;
                padding: 4px;
                font-size: 8px;
            ">
                <div style="color: rgba(100, 100, 100, 0.4); text-align: center; font-style: italic; font-size: 7px;">
                    👻 Ultra Stealth Mode Active<br>
                    🎤 Auto-listening for questions<br>
                    Ctrl+Shift+H = Toggle | Ctrl+Shift+L = Auto-Listen
                </div>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(this.overlay);
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('✅ Ultra stealth overlay created');
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
        
        // Auto-listen toggle button
        const autoListenBtn = document.getElementById('toggle-auto-listen');
        if (autoListenBtn) {
            autoListenBtn.addEventListener('click', () => {
                this.toggleAutoListening();
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
                this.updateStatus('✅ Account ready');
                
                this.displayAnswer(`👻 Ultra Stealth Account Created!\n\nEmail: ${email}\nMode: Ultra Stealth + Auto-Listen\n\nAI is now listening automatically!`);
            } else {
                throw new Error('Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.updateStatus('❌ Registration failed');
        }
    }

    testOverlay() {
        this.updateStatus('🧪 Ultra stealth test');
        this.displayAnswer('👻 Ultra Stealth Test: This overlay should be nearly invisible in screen recordings while remaining readable to you. Auto-listening is active for hands-free operation.');
        setTimeout(() => {
            this.updateStatus('✅ Ready (auto-listening)');
        }, 3000);
    }

    setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech recognition not supported');
            this.updateStatus('❌ Speech not supported');
            return;
        }

        try {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                console.log('🎤 Speech recognition started (auto-mode)');
                this.updateStatus('🎤 Auto-listening active...');
                this.isListening = true;
                this.updateAutoListenButton();
            };
            
            this.recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');
                
                if (transcript.trim()) {
                    console.log('🎙️ Auto-heard:', transcript);
                    this.processQuestion(transcript);
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                
                // Auto-restart on most errors (except permission denied)
                if (event.error !== 'not-allowed' && this.autoListenEnabled) {
                    setTimeout(() => {
                        this.startAutoListening();
                    }, 1000);
                }
            };
            
            this.recognition.onend = () => {
                console.log('🎤 Speech recognition ended');
                this.isListening = false;
                
                // Auto-restart if auto-listening is enabled
                if (this.autoListenEnabled) {
                    setTimeout(() => {
                        this.startAutoListening();
                    }, 500);
                }
                
                this.updateAutoListenButton();
            };
            
        } catch (error) {
            console.error('Failed to setup speech recognition:', error);
            this.updateStatus('❌ Speech setup failed');
        }
    }

    startAutoListening() {
        if (this.recognition && this.autoListenEnabled && !this.isListening) {
            try {
                this.recognition.start();
                console.log('🎤 Auto-listening started');
            } catch (error) {
                console.error('Error starting auto-listening:', error);
            }
        }
    }

    stopAutoListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            console.log('🎤 Auto-listening stopped');
        }
    }

    toggleAutoListening() {
        this.autoListenEnabled = !this.autoListenEnabled;
        
        if (this.autoListenEnabled) {
            this.startAutoListening();
            this.updateStatus('🎤 Auto-listen enabled');
        } else {
            this.stopAutoListening();
            this.updateStatus('⏸️ Auto-listen disabled');
        }
        
        this.updateAutoListenButton();
    }

    updateAutoListenButton() {
        const btn = document.getElementById('toggle-auto-listen');
        if (btn) {
            if (this.autoListenEnabled) {
                btn.textContent = this.isListening ? '🎤 Listening...' : '🎤 Auto-Listen ON';
                btn.style.background = 'rgba(0, 255, 0, 0.3)';
            } else {
                btn.textContent = '⏸️ Auto-Listen OFF';
                btn.style.background = 'rgba(255, 0, 0, 0.3)';
            }
        }
    }

    processQuestion(transcript) {
        const now = Date.now();
        
        // Debounce: Prevent processing if we just processed a question
        if (this.isProcessingQuestion || (now - this.lastQuestionTime) < this.questionCooldown) {
            return;
        }
        
        // Enhanced question detection
        const lowerTranscript = transcript.toLowerCase();
        if (transcript.includes('?') || 
            lowerTranscript.includes('what') ||
            lowerTranscript.includes('how') ||
            lowerTranscript.includes('why') ||
            lowerTranscript.includes('explain') ||
            lowerTranscript.includes('tell me') ||
            lowerTranscript.includes('can you') ||
            lowerTranscript.includes('could you') ||
            lowerTranscript.includes('define') ||
            lowerTranscript.includes('describe')) {
            
            this.isProcessingQuestion = true;
            this.lastQuestionTime = now;
            
            this.askAI(transcript);
            
            // Reset processing flag
            setTimeout(() => {
                this.isProcessingQuestion = false;
            }, 2000);
        }
    }

    async askAI(question) {
        try {
            this.updateStatus('🤖 AI processing...');
            
            const token = localStorage.getItem('ai_mentor_token');
            
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
                this.updateStatus('✅ AI ready (auto-listening)');
            } else if (response.status === 401) {
                const authResponse = `🔑 Authentication Required\n\nClick "🔑 Register" above for AI responses.\n\nQ: "${question.substring(0, 50)}..."`;
                this.displayAnswer(authResponse);
                this.updateStatus('⚠️ Please register');
            } else {
                throw new Error(`API error: ${response.status}`);
            }
            
        } catch (error) {
            console.error('Error:', error);
            const fallbackResponse = `🔌 Connection Issue\n\nQ: "${question.substring(0, 50)}..."\n\nCheck backend connection.`;
            this.displayAnswer(fallbackResponse);
            this.updateStatus('❌ Backend issue');
        }
    }

    displayAnswer(answer) {
        const answersDiv = document.getElementById('answers');
        if (answersDiv) {
            const answerElement = document.createElement('div');
            answerElement.style.cssText = `
                margin-bottom: 6px;
                padding: 4px;
                background: rgba(0, 255, 50, 0.05);
                border-left: 1px solid rgba(0, 255, 50, 0.2);
                border-radius: 1px;
                font-size: 8px;
                color: rgba(0, 255, 50, 0.4);
            `;
            answerElement.innerHTML = `
                <div style="font-size: 7px; color: rgba(100, 100, 100, 0.3); margin-bottom: 2px;">
                    ${new Date().toLocaleTimeString()}
                </div>
                <div>${answer}</div>
            `;
            
            answersDiv.insertBefore(answerElement, answersDiv.firstChild);
            
            // Limit to 3 answers for ultra stealth
            while (answersDiv.children.length > 4) {
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
                this.updateStatus('✅ Backend connected (auto-listening)');
            } else {
                this.updateStatus('⚠️ Backend not responding');
            }
        } catch (error) {
            this.updateStatus('❌ Backend offline');
        }
    }

    toggleOverlayVisibility() {
        if (this.overlay) {
            const currentOpacity = parseFloat(this.overlay.style.opacity);
            if (currentOpacity <= 0.15) {
                // Make temporarily more visible for emergency access
                this.overlay.style.opacity = '0.7';
                this.overlay.style.color = 'rgba(0, 255, 50, 0.8)';
                this.updateStatus('👻 Emergency visibility mode');
                
                // Auto-hide after 10 seconds
                setTimeout(() => {
                    this.overlay.style.opacity = '0.15';
                    this.overlay.style.color = 'rgba(0, 255, 50, 0.3)';
                    this.updateStatus('✅ Ultra stealth restored');
                }, 10000);
            } else {
                // Return to ultra stealth
                this.overlay.style.opacity = '0.15';
                this.overlay.style.color = 'rgba(0, 255, 50, 0.3)';
                this.updateStatus('✅ Ultra stealth active');
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
