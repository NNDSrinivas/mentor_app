// AI Interview Assistant - BALANCED STEALTH MODE
// Visible to you but discrete during screen sharing + auto-listening

// Prevent multiple instances
if (window.aiInterviewAssistantLoaded) {
    console.log('🥷 AI Interview Assistant already loaded, skipping...');
} else {
    window.aiInterviewAssistantLoaded = true;
    
    console.log('🥷 AI Interview Assistant (BALANCED STEALTH) Loading...');

    class AIInterviewAssistant {
        constructor() {
            this.isListening = false;
            this.recognition = null;
            this.overlay = null;
            this.isProcessingQuestion = false;
            this.lastQuestionTime = 0;
            this.questionCooldown = 3000; // 3 second cooldown
            this.autoListenEnabled = true; // Auto-listening enabled by default
            
            console.log('🥷 AI Interview Assistant initialized in BALANCED STEALTH MODE');
        }

        initialize() {
            console.log('🔧 Initializing AI Interview Assistant in BALANCED STEALTH MODE...');
            
            // Create balanced stealth overlay
            this.createBalancedStealthOverlay();
            
            // Initialize speech recognition with auto-start
            this.setupSpeechRecognition();
            
            // Check backend connection
            this.checkBackend();
            
            // Set up hotkeys
            this.setupHotkeys();

            // Detect display sharing to avoid leaking overlay
            this.setupDisplayShareDetection();
            
            // Auto-start listening after initialization
            setTimeout(() => {
                if (this.autoListenEnabled && this.recognition) {
                    this.startAutoListening();
                }
            }, 2000);
            
            console.log('✅ AI Interview Assistant fully initialized in BALANCED STEALTH MODE');
        }

        setupHotkeys() {
            document.addEventListener('keydown', (e) => {
                // Ctrl+Shift+H to toggle overlay visibility (show/hide completely)
                if (e.ctrlKey && e.shiftKey && e.key === 'H') {
                    e.preventDefault();
                    this.toggleOverlayVisibility();
                    console.log('🥷 Overlay visibility toggled');
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
                
                // Ctrl+Shift+S to toggle stealth level
                if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                    e.preventDefault();
                    this.toggleStealthLevel();
                    console.log('🥷 Stealth level toggled');
                }
            });
        }

        setupDisplayShareDetection() {
            // Inject in-page hook for getDisplayMedia to detect full screen sharing
            const script = document.createElement('script');
            script.textContent = `(() => {
                const orig = navigator.mediaDevices.getDisplayMedia;
                if (!orig) return;
                navigator.mediaDevices.getDisplayMedia = async function(...args){
                    const stream = await orig.apply(this, args);
                    try {
                        const track = stream.getVideoTracks()[0];
                        const label = (track && track.label || '').toLowerCase();
                        const mode = label.includes('screen') ? 'display' : 'window';
                        window.postMessage({type: '__aim_share_mode', mode}, '*');
                    } catch(e){}
                    return stream;
                };
            })();`;
            document.documentElement.appendChild(script);
            script.remove();

            window.addEventListener('message', (event) => {
                if (event.data && event.data.type === '__aim_share_mode') {
                    chrome.runtime.sendMessage({
                        type: 'aim_full_display_share',
                        data: { mode: event.data.mode }
                    });
                }
            });
        }

        createBalancedStealthOverlay() {
            // Remove existing overlay
            const existing = document.getElementById('ai-assistant-overlay');
            if (existing) existing.remove();

            // Create balanced stealth overlay - visible to you, discrete for screen capture
            this.overlay = document.createElement('div');
            this.overlay.id = 'ai-assistant-overlay';
            
            // BALANCED STEALTH: Visible to you but discrete in recordings
            this.overlay.style.cssText = `
                position: fixed !important;
                top: 20px !important;
                right: 20px !important;
                width: 320px !important;
                max-height: 450px !important;
                z-index: 2147483647 !important;
                font-family: 'Courier New', monospace !important;
                font-size: 11px !important;
                padding: 10px !important;
                overflow-y: auto !important;
                pointer-events: auto !important;
                
                /* BALANCED STEALTH TECHNIQUES */
                background: linear-gradient(135deg, rgba(0, 20, 0, 0.85), rgba(0, 40, 0, 0.85)) !important;
                color: rgba(0, 255, 50, 0.85) !important;
                border: 1px solid rgba(0, 255, 50, 0.4) !important;
                border-radius: 6px !important;
                box-shadow: 0 2px 10px rgba(0, 255, 50, 0.15) !important;
                
                /* Screen capture discretion while maintaining visibility */
                opacity: 0.85 !important;
                filter: contrast(0.9) brightness(0.8) !important;
                
                /* Subtle effects */
                backdrop-filter: blur(1px) !important;
                text-shadow: 0 0 3px rgba(0, 255, 50, 0.3) !important;
            `;
            
            this.overlay.innerHTML = `
                <div style="text-align: center; margin-bottom: 8px; color: #00ff32; font-weight: bold; font-size: 12px;">
                    🥷 AI Assistant (Balanced Stealth)
                </div>
                
                <div style="text-align: center; margin-bottom: 8px; font-size: 9px; color: #ffcc00; border: 1px solid rgba(255, 204, 0, 0.4); padding: 3px; border-radius: 3px; background: rgba(255, 204, 0, 0.1);">
                    🔒 Discrete Mode - Visible to you
                </div>
                
                <div id="status" style="
                    text-align: center;
                    padding: 6px;
                    background: rgba(0, 255, 50, 0.15);
                    border: 1px solid rgba(0, 255, 50, 0.3);
                    border-radius: 4px;
                    margin-bottom: 8px;
                    font-size: 10px;
                    color: #00ff32;
                ">
                    🔧 Initializing...
                </div>
                
                <div style="margin-bottom: 8px;">
                    <button id="register-btn" style="
                        width: 100%;
                        padding: 5px;
                        background: rgba(0, 136, 255, 0.7);
                        color: white;
                        border: 1px solid rgba(0, 136, 255, 0.5);
                        border-radius: 4px;
                        font-weight: bold;
                        cursor: pointer;
                        margin-bottom: 4px;
                        font-size: 10px;
                    ">🔑 Quick Register</button>
                    
                    <button id="toggle-auto-listen" style="
                        width: 100%;
                        padding: 5px;
                        background: rgba(255, 136, 0, 0.7);
                        color: white;
                        border: 1px solid rgba(255, 136, 0, 0.5);
                        border-radius: 4px;
                        font-weight: bold;
                        cursor: pointer;
                        margin-bottom: 4px;
                        font-size: 10px;
                    ">🎤 Auto-Listen ON</button>
                    
                    <button id="test-btn" style="
                        width: 100%;
                        padding: 5px;
                        background: rgba(0, 255, 50, 0.7);
                        color: black;
                        border: 1px solid rgba(0, 255, 50, 0.5);
                        border-radius: 4px;
                        font-weight: bold;
                        cursor: pointer;
                        font-size: 10px;
                    ">🧪 Test</button>
                </div>
                
                <div id="answers" style="
                    max-height: 220px;
                    overflow-y: auto;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(0, 255, 50, 0.3);
                    border-radius: 4px;
                    padding: 6px;
                    font-size: 10px;
                ">
                    <div style="color: rgba(150, 150, 150, 0.8); text-align: center; font-style: italic; font-size: 9px;">
                        🥷 Balanced Stealth Mode Active<br>
                        🎤 Auto-listening for questions...<br>
                        <br>
                        <strong>Hotkeys:</strong><br>
                        Ctrl+Shift+H = Show/Hide<br>
                        Ctrl+Shift+L = Auto-Listen Toggle<br>
                        Ctrl+Shift+S = Stealth Level<br>
                        Ctrl+Shift+T = Test
                    </div>
                </div>
            `;
            
            // Add to page
            document.body.appendChild(this.overlay);
            
            // Set up event listeners
            this.setupEventListeners();
            
            console.log('✅ Balanced stealth overlay created and visible');
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
                
                const email = `balanced${Date.now()}@aimentor.com`;
                const password = 'balanced123456';
                
                const response = await fetch('http://localhost:8084/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('ai_mentor_token', data.token);
                    this.updateStatus('✅ Account ready');
                    
                    this.displayAnswer(`🥷 Balanced Stealth Account Created!\n\nEmail: ${email}\nMode: Balanced Stealth + Auto-Listen\n\nAI is now listening automatically! Try asking a question.`);
                } else {
                    throw new Error('Registration failed');
                }
            } catch (error) {
                console.error('Registration error:', error);
                this.updateStatus('❌ Registration failed');
            }
        }

        testOverlay() {
            this.updateStatus('🧪 Testing balanced stealth...');
            this.displayAnswer('🥷 Balanced Stealth Test: This overlay is clearly visible to you but designed to be discrete during screen recordings. Auto-listening is active - try asking "What is Python?" to test AI responses.');
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
                    this.updateStatus(`❌ Speech error: ${event.error}`);
                    
                    // Auto-restart on most errors (except permission denied)
                    if (event.error !== 'not-allowed' && this.autoListenEnabled) {
                        setTimeout(() => {
                            this.startAutoListening();
                        }, 2000);
                    }
                };
                
                this.recognition.onend = () => {
                    console.log('🎤 Speech recognition ended');
                    this.isListening = false;
                    
                    // Auto-restart if auto-listening is enabled
                    if (this.autoListenEnabled) {
                        setTimeout(() => {
                            this.startAutoListening();
                        }, 1000);
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
                    this.updateStatus('❌ Could not start listening');
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
                    btn.style.background = 'rgba(0, 255, 0, 0.7)';
                } else {
                    btn.textContent = '⏸️ Auto-Listen OFF';
                    btn.style.background = 'rgba(255, 0, 0, 0.7)';
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
                
                // Show detected question
                this.updateStatus(`🎙️ Question detected: "${transcript.substring(0, 30)}..."`);
                
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
                    const authResponse = `🔑 Authentication Required\n\nClick "🔑 Quick Register" above for AI responses.\n\nQ: "${question.substring(0, 50)}..."`;
                    this.displayAnswer(authResponse);
                    this.updateStatus('⚠️ Please register for AI');
                } else {
                    throw new Error(`API error: ${response.status}`);
                }
                
            } catch (error) {
                console.error('Error:', error);
                const fallbackResponse = `🔌 Connection Issue\n\nQ: "${question.substring(0, 50)}..."\n\nBackend may be offline. Check terminal.`;
                this.displayAnswer(fallbackResponse);
                this.updateStatus('❌ Backend connection failed');
            }
        }

        displayAnswer(answer) {
            const answersDiv = document.getElementById('answers');
            if (answersDiv) {
                const answerElement = document.createElement('div');
                answerElement.style.cssText = `
                    margin-bottom: 8px;
                    padding: 6px;
                    background: rgba(0, 255, 50, 0.1);
                    border-left: 2px solid rgba(0, 255, 50, 0.4);
                    border-radius: 3px;
                    font-size: 10px;
                    color: rgba(0, 255, 50, 0.9);
                `;
                answerElement.innerHTML = `
                    <div style="font-size: 8px; color: rgba(150, 150, 150, 0.6); margin-bottom: 3px;">
                        ${new Date().toLocaleTimeString()}
                    </div>
                    <div>${answer}</div>
                `;
                
                answersDiv.insertBefore(answerElement, answersDiv.firstChild);
                
                // Limit to 4 answers to keep overlay manageable
                while (answersDiv.children.length > 5) {
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
                    this.updateStatus('✅ Backend connected - Ready!');
                } else {
                    this.updateStatus('⚠️ Backend not responding');
                }
            } catch (error) {
                this.updateStatus('❌ Backend offline - Start server');
            }
        }

        toggleOverlayVisibility() {
            if (this.overlay) {
                if (this.overlay.style.display === 'none') {
                    this.overlay.style.display = 'block';
                    this.updateStatus('👁️ Overlay shown');
                } else {
                    this.overlay.style.display = 'none';
                    console.log('🙈 Overlay hidden - Use Ctrl+Shift+H to show');
                }
            }
        }

        toggleStealthLevel() {
            if (this.overlay) {
                const currentOpacity = parseFloat(this.overlay.style.opacity);
                if (currentOpacity >= 0.85) {
                    // High stealth mode
                    this.overlay.style.opacity = '0.4';
                    this.overlay.style.color = 'rgba(0, 255, 50, 0.4)';
                    this.updateStatus('🥷 High stealth mode');
                } else {
                    // Normal visibility
                    this.overlay.style.opacity = '0.85';
                    this.overlay.style.color = 'rgba(0, 255, 50, 0.85)';
                    this.updateStatus('👁️ Normal visibility');
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
}
