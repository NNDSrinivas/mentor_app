// Content script for meeting platforms - AI Interview Assistant
// This version implements intelligent answer persistence and proper stealth mode

console.log('🤖 AI Mentor Content Script Loading...');

// Prevent multiple initializations
if (window.AIMentorInitialized) {
    console.log('🔄 AI Mentor already initialized, skipping...');
} else {
    window.AIMentorInitialized = true;
    
    class MeetingAIAssistant {
        constructor() {
            console.log('🚀 AI Mentor Assistant - Starting initialization');
            this.isActive = false;
            this.meetingPlatform = this.detectPlatform();
            this.aiSocket = null;
            this.overlay = null;
            this.bridge = null;
            this.answerPersistenceTimer = null;
            this.answerFadeTimer = null;
            this.lastQuestion = null;
            this.meetingData = {
                participants: [],
                chatHistory: [],
                jiraTickets: [],
                screenShareActive: false
            };
            console.log('🎯 Platform detected:', this.meetingPlatform);
            this.init();
        }

        detectPlatform() {
            const hostname = window.location.hostname;
            console.log('🔍 Detecting platform for:', hostname);
            if (hostname.includes('zoom.us')) return 'zoom';
            if (hostname.includes('teams.microsoft.com')) return 'teams';
            if (hostname.includes('meet.google.com')) return 'google-meet';
            if (hostname.includes('webex.com')) return 'webex';
            return 'unknown';
        }

        async init() {
            try {
                console.log('🎯 Creating stealth interview overlay...');
                this.createStealthInterviewOverlay();
                
                console.log('🔗 Connecting to AI service...');
                await this.connectToAI();
                
                console.log('🎤 Starting meeting monitoring...');
                this.startMeetingMonitoring();
                
                console.log('✅ AI Mentor Assistant initialized successfully');
            } catch (error) {
                console.error('❌ Failed to initialize AI Mentor:', error);
            }
        }

        createStealthInterviewOverlay() {
            console.log('🕵️ Creating stealth interview overlay...');
            
            if (this.overlay) {
                this.overlay.remove();
            }
            
            this.overlay = document.createElement('div');
            this.overlay.id = 'ai-interview-stealth-overlay';
            
            // Ultra-stealth CSS - Always visible to you, hidden from screen sharing
            this.overlay.style.cssText = `
                position: fixed !important;
                top: 10px !important;
                right: 10px !important;
                width: 420px !important;
                height: 550px !important;
                background: rgba(0, 0, 0, 0.98) !important;
                color: #00ff00 !important;
                font-family: 'Courier New', monospace !important;
                font-size: 12px !important;
                z-index: 2147483647 !important;
                border-radius: 15px !important;
                border: 2px solid rgba(0, 255, 0, 0.8) !important;
                backdrop-filter: blur(20px) !important;
                box-shadow: 0 0 50px rgba(0, 255, 0, 0.3) !important;
                user-select: none !important;
                pointer-events: auto !important;
                opacity: 0.95 !important;
                visibility: visible !important;
                display: block !important;
                transform: scale(1) !important;
                transition: all 0.3s ease !important;
                overflow: hidden !important;
            `;
            
            this.overlay.innerHTML = `
                <div class="stealth-content">
                    <div class="stealth-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid rgba(0, 255, 0, 0.3); padding-bottom: 8px;">
                        <div style="display: flex; align-items: center;">
                            <span style="font-size: 14px; margin-right: 8px;">🤖</span>
                            <span style="font-weight: 600; color: #00ff00; text-shadow: 0 0 8px rgba(0, 255, 0, 0.4);">Interview Assistant</span>
                        </div>
                        <button id="stealth-minimize" style="background: transparent; border: 1px solid #00ff00; color: #00ff00; border-radius: 3px; padding: 2px 6px; cursor: pointer; font-weight: bold; font-size: 10px;">─</button>
                    </div>
                    
                    <div id="ai-status" style="font-size: 10px; color: #888; margin-bottom: 10px; text-align: center;">
                        🔄 Initializing...
                    </div>
                    
                    <div id="interview-content" style="height: calc(100% - 60px); overflow: hidden;">
                        <div style="text-align: center; padding: 30px; color: #888;">
                            <div style="font-size: 20px; margin-bottom: 15px;">👂</div>
                            <div style="margin-bottom: 10px;">AI Interview Assistant Ready</div>
                            <div style="font-size: 10px;">
                                • Listens to interviewer questions<br>
                                • Provides instant answers for your reference<br>
                                • ALWAYS visible to YOU (the user)<br>
                                • Hidden from screen sharing/recording<br>
                                • Emergency hide: Ctrl+Shift+A<br>
                                <br>
                                <strong>Test:</strong> Say "Hi how are you" or "Tell me about yourself"
                            </div>
                        </div>
                        
                        <div id="current-question" style="display: none; margin-bottom: 10px; padding: 8px; background: rgba(0, 100, 255, 0.1); border-left: 3px solid #0066ff; font-size: 11px;"></div>
                        <div id="ai-answer" style="height: 300px; overflow-y: auto; padding: 10px; background: rgba(0, 0, 0, 0.3); border-radius: 8px; font-size: 11px; line-height: 1.4; display: none;"></div>
                        <div style="display: flex; align-items: center; margin-top: 10px; font-size: 10px; color: #666;">
                            <span>🎯 Reading Progress:</span>
                            <div style="flex: 1; height: 3px; background: rgba(0, 255, 0, 0.2); border-radius: 2px; overflow: hidden; position: relative;">
                                <div id="confidence-bar" style="height: 100%; background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #feca57); width: 0%; transition: width 0.3s ease; animation: confidencePulse 2s infinite;"></div>
                            </div>
                            <span id="confidence-text" style="margin-left: 8px; min-width: 40px;">Ready</span>
                        </div>
                    </div>
                </div>
            `;
            
            // Add enhanced stealth styles
            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes confidencePulse {
                    0%, 100% { opacity: 0.6; }
                    50% { opacity: 1; }
                }
                
                /* Normal state - ALWAYS visible to user */
                #ai-interview-stealth-overlay {
                    visibility: visible !important;
                    display: block !important;
                    opacity: 0.95 !important;
                }
                
                /* Stealth mode - Hidden from screen capture but visible to user */
                #ai-interview-stealth-overlay.screen-sharing {
                    mix-blend-mode: difference;
                    filter: invert(1) hue-rotate(180deg) contrast(2) saturate(0.1);
                    -webkit-transform: translateZ(0) rotateY(0.01deg);
                    -webkit-backface-visibility: hidden;
                    transform-style: preserve-3d;
                    isolation: isolate;
                    contain: strict;
                    --stealth-opacity: 0.95;
                    opacity: var(--stealth-opacity) !important;
                    z-index: 2147483647 !important;
                    position: fixed !important;
                }
                
                /* Emergency manual hide state (Ctrl+Shift+A) */
                #ai-interview-stealth-overlay.manually-hidden {
                    opacity: 0 !important;
                    pointer-events: none !important;
                    visibility: hidden !important;
                }
                
                .question-display.active {
                    display: block !important;
                    animation: questionSlideIn 0.4s ease-out;
                }
                
                @keyframes questionSlideIn {
                    from { 
                        opacity: 0;
                        transform: translateY(-8px);
                    }
                    to { 
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .typing-cursor::after {
                    content: '▋';
                    color: #00ff00;
                    animation: blink 1s infinite;
                }
                
                @keyframes blink {
                    0%, 50% { opacity: 1; }
                    51%, 100% { opacity: 0; }
                }
                
                #ai-answer::-webkit-scrollbar {
                    width: 6px;
                }
                
                #ai-answer::-webkit-scrollbar-track {
                    background: rgba(0, 255, 0, 0.1);
                }
                
                #ai-answer::-webkit-scrollbar-thumb {
                    background: rgba(0, 255, 0, 0.5);
                    border-radius: 3px;
                }
                
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
                    50% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
                    100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
                }
            `;
            
            document.head.appendChild(style);
            document.body.appendChild(this.overlay);
            this.initializeStealthFeatures();
            
            console.log('🕵️ Stealth interview overlay created - Always visible to you, hidden from screen sharing');
        }

        initializeStealthFeatures() {
            // Setup minimize functionality
            const minimizeBtn = document.getElementById('stealth-minimize');
            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', () => {
                    this.overlay.classList.toggle('minimized');
                });
            }
            
            // Initialize stealth state - ALWAYS VISIBLE TO YOU
            this.stealthState = {
                alwaysVisibleToUser: true,
                hiddenFromScreenShare: false,
                manuallyHidden: false
            };
            
            // Initialize interview mode settings with intelligent persistence
            this.interviewMode = {
                isActive: false,
                currentQuestion: '',
                isTyping: false,
                typingSpeed: 80,
                speakerDetection: {
                    userSpeaking: false,
                    interviewerSpeaking: false,
                    lastSpeechTime: 0
                },
                answerState: {
                    isDisplayed: false,
                    userIsReading: false,
                    readingStartTime: null,
                    readingCompleted: false,
                    lastActivity: Date.now()
                }
            };
            
            // Setup keyboard controls for stealth toggle
            this.setupKeyboardControls();
            
            // Setup stealth protection
            this.setupStealthProtection();
            
            console.log('🔒 Stealth features initialized:');
            console.log('   ✅ ALWAYS visible to YOU (the user)');
            console.log('   🕵️ Hidden from screen sharing automatically'); 
            console.log('   ⌨️ Ctrl+Shift+A = Emergency manual toggle');
            console.log('   🧠 Intelligent answer persistence enabled');
        }

        setupKeyboardControls() {
            console.log('⌨️ Setting up keyboard controls...');
            
            document.addEventListener('keydown', (event) => {
                if (event.ctrlKey && event.shiftKey && event.code === 'KeyA') {
                    event.preventDefault();
                    this.toggleManualStealth();
                }
            });
            
            console.log('✅ Keyboard controls ready: Ctrl+Shift+A = Emergency toggle');
        }

        toggleManualStealth() {
            this.stealthState.manuallyHidden = !this.stealthState.manuallyHidden;
            
            if (this.stealthState.manuallyHidden) {
                console.log('🫥 EMERGENCY: Manually hiding overlay from YOU (Ctrl+Shift+A to show again)');
                this.overlay.classList.add('manually-hidden');
                this.showTemporaryNotification('🫥 AI Assistant hidden (Ctrl+Shift+A to show)', 2000);
            } else {
                console.log('👁️ RESTORED: Overlay visible to YOU again');
                this.overlay.classList.remove('manually-hidden');
                this.showTemporaryNotification('👁️ AI Assistant visible', 2000);
            }
        }

        showTemporaryNotification(message, duration = 3000) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                background: rgba(0, 0, 0, 0.9) !important;
                color: #00ff00 !important;
                padding: 15px 25px !important;
                border-radius: 10px !important;
                border: 2px solid #00ff00 !important;
                font-family: 'Courier New', monospace !important;
                font-size: 14px !important;
                font-weight: bold !important;
                z-index: 2147483648 !important;
                text-align: center !important;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.5) !important;
                animation: fadeInOut 0.3s ease !important;
            `;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }

        setupStealthProtection() {
            const overlay = this.overlay;
            
            let mediaDevices = navigator.mediaDevices;
            if (mediaDevices && mediaDevices.getDisplayMedia) {
                const originalGetDisplayMedia = mediaDevices.getDisplayMedia.bind(mediaDevices);
                mediaDevices.getDisplayMedia = function(constraints) {
                    console.log('🖥️ SCREEN SHARING DETECTED');
                    console.log('   👁️ Overlay remains VISIBLE to YOU');
                    console.log('   🕵️ Overlay becomes HIDDEN from screen capture');
                    
                    overlay.classList.add('screen-sharing');
                    this.stealthState.hiddenFromScreenShare = true;
                    this.showTemporaryNotification('🕵️ Stealth mode ON - Hidden from screen sharing', 3000);
                    
                    return originalGetDisplayMedia(constraints).then(stream => {
                        stream.getTracks().forEach(track => {
                            track.onended = () => {
                                console.log('✅ SCREEN SHARING ENDED');
                                overlay.classList.remove('screen-sharing');
                                this.stealthState.hiddenFromScreenShare = false;
                                this.showTemporaryNotification('🔍 Stealth mode OFF', 2000);
                            };
                        });
                        return stream;
                    });
                }.bind(this);
            }
            
            overlay.style.userSelect = 'none';
            overlay.style.webkitUserSelect = 'none';
            overlay.setAttribute('data-stealth', 'interview-assistant');
            overlay.setAttribute('data-user-visible', 'always');
            
            console.log('✅ Stealth protection active');
        }

        async connectToAI() {
            try {
                console.log('🔗 Connecting to AI service...');
                const response = await fetch('http://localhost:8084/api/health');
                if (response.ok) {
                    this.updateStatus('🤖 AI Connected - Ready to assist');
                    this.isActive = true;
                    console.log('✅ AI service connected successfully');
                } else {
                    throw new Error('AI service not available');
                }
            } catch (error) {
                this.updateStatus('❌ AI Offline - Start mentor app');
                console.error('❌ Failed to connect to AI:', error);
            }
        }

        startMeetingMonitoring() {
            if (!this.isActive) return;
            
            switch (this.meetingPlatform) {
                case 'zoom':
                case 'teams':
                case 'google-meet':
                case 'webex':
                    this.monitorMeeting();
                    break;
                default:
                    this.monitorGeneric();
            }
        }

        monitorMeeting() {
            console.log('🎤 Setting up meeting monitoring with speech recognition...');
            this.startAudioMonitoring();
            this.updateStatus('🎤 Monitoring meeting + Audio');
        }

        async startAudioMonitoring() {
            console.log('🎤 Starting audio monitoring with intelligent persistence...');
            this.updateStatus('🔧 Initializing voice recognition...');
            
            try {
                console.log('🎤 Requesting microphone permission...');
                
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    }
                });
                
                console.log('✅ Microphone permission granted');
                stream.getTracks().forEach(track => track.stop());
                await this.initializeSpeechRecognition();
                
            } catch (error) {
                console.error('❌ Voice recognition setup failed:', error);
                this.showVoiceRecognitionFallback();
            }
        }

        async initializeSpeechRecognition() {
            console.log('🎤 Setting up speech recognition...');
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                console.error('❌ Speech recognition not supported');
                this.showVoiceRecognitionFallback();
                return;
            }

            try {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.recognition = new SpeechRecognition();
                
                this.recognition.continuous = true;
                this.recognition.interimResults = true;
                this.recognition.maxAlternatives = 1;
                this.recognition.lang = 'en-US';
                
                let restartTimeout;
                
                this.recognition.onstart = () => {
                    console.log('🎤 Voice recognition started - ready to listen');
                    this.updateStatus('🎤 Listening for questions...');
                    this.showVoiceRecognitionWorking();
                };
                
                this.recognition.onresult = (event) => {
                    this.handleVoiceResult(event);
                };
                
                this.recognition.onerror = (event) => {
                    console.error('🎤 Voice recognition error:', event.error);
                    
                    if (event.error === 'not-allowed') {
                        this.updateStatus('❌ Microphone permission denied');
                        this.showVoiceRecognitionFallback();
                        return;
                    }
                    
                    this.updateStatus(`⚠️ Voice error: ${event.error} - Restarting...`);
                    clearTimeout(restartTimeout);
                    restartTimeout = setTimeout(() => {
                        console.log('🔄 Restarting voice recognition...');
                        this.recognition.start();
                    }, 1000);
                };
                
                this.recognition.onend = () => {
                    console.log('🎤 Voice recognition ended - restarting...');
                    clearTimeout(restartTimeout);
                    restartTimeout = setTimeout(() => {
                        if (this.recognition) {
                            this.recognition.start();
                        }
                    }, 100);
                };

                this.recognition.start();
                console.log('✅ Voice recognition initialized');
                
            } catch (error) {
                console.error('❌ Failed to start speech recognition:', error);
                this.showVoiceRecognitionFallback();
            }
        }

        handleVoiceResult(event) {
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                }
            }
            
            if (finalTranscript.trim()) {
                console.log('🎤 Final transcript:', finalTranscript);
                
                // Check if user is reading back an answer
                if (this.interviewMode.answerState.isDisplayed) {
                    this.detectUserReadingAnswer(finalTranscript);
                }
                
                // Detect if this is a question or user response
                if (this.isInterviewQuestion(finalTranscript)) {
                    console.log('❓ New question detected:', finalTranscript);
                    this.updateStatus('🧠 Processing interview question...');
                    this.getInterviewAIResponse(finalTranscript);
                } else if (this.interviewMode.answerState.isDisplayed) {
                    console.log('💬 User is responding to interviewer');
                    this.handleUserResponse(finalTranscript);
                } else {
                    console.log('💬 General conversation:', finalTranscript);
                    this.updateStatus('🎤 Listening for questions...');
                }
                
                this.interviewMode.answerState.lastActivity = Date.now();
            }
        }

        detectUserReadingAnswer(transcript) {
            const answerDisplay = document.getElementById('ai-answer');
            if (!answerDisplay || !answerDisplay.textContent) return;
            
            const answerText = answerDisplay.textContent.toLowerCase();
            const userText = transcript.toLowerCase();
            
            const answerWords = answerText.split(' ').filter(w => w.length > 3);
            const userWords = userText.split(' ').filter(w => w.length > 3);
            
            let matchingWords = 0;
            userWords.forEach(userWord => {
                if (answerWords.some(answerWord => 
                    answerWord.includes(userWord) || userWord.includes(answerWord))) {
                    matchingWords++;
                }
            });
            
            const matchPercentage = matchingWords / Math.max(userWords.length, 1);
            
            if (matchPercentage > 0.3) {
                console.log('📖 DETECTED: User is reading the AI answer back to interviewer');
                this.markUserAsReading();
                this.extendAnswerPersistence('User is reading answer');
            } else if (userWords.length > 5) {
                console.log('💭 User is elaborating or explaining further');
                this.extendAnswerPersistence('User is elaborating');
            }
        }

        handleUserResponse(transcript) {
            console.log('🗣️ User is responding to interviewer');
            this.extendAnswerPersistence('User is responding');
            
            const completionPhrases = [
                'thank you', 'that\'s all', 'does that answer', 'any other questions',
                'anything else', 'is there anything', 'what else'
            ];
            
            const isComplete = completionPhrases.some(phrase => 
                transcript.toLowerCase().includes(phrase));
            
            if (isComplete) {
                console.log('✅ User seems to have completed their response');
                this.scheduleAnswerFade(10000);
            }
        }

        markUserAsReading() {
            if (!this.interviewMode.answerState.userIsReading) {
                this.interviewMode.answerState.userIsReading = true;
                this.interviewMode.answerState.readingStartTime = Date.now();
                
                const answerDisplay = document.getElementById('ai-answer');
                if (answerDisplay) {
                    answerDisplay.style.borderLeft = '4px solid #00ff00';
                    answerDisplay.style.boxShadow = '0 0 10px rgba(0, 255, 0, 0.3)';
                }
                
                this.updateInterviewStatus('📖 User is reading answer to interviewer');
                console.log('📖 User reading detected - keeping answer visible');
            }
        }

        extendAnswerPersistence(reason) {
            if (this.answerPersistenceTimer) {
                clearTimeout(this.answerPersistenceTimer);
            }
            if (this.answerFadeTimer) {
                clearTimeout(this.answerFadeTimer);
            }
            
            const answerDisplay = document.getElementById('ai-answer');
            if (answerDisplay) {
                answerDisplay.style.opacity = '1';
                answerDisplay.style.backgroundColor = 'rgba(0, 255, 0, 0.05)';
            }
            
            console.log(`⏰ Answer persistence extended: ${reason}`);
            this.updateInterviewStatus(`⏰ Keeping answer visible: ${reason}`);
            
            this.scheduleAnswerFade(30000);
        }

        scheduleAnswerFade(delay) {
            this.answerFadeTimer = setTimeout(() => {
                this.gradualAnswerFade();
            }, delay);
        }

        gradualAnswerFade() {
            const answerDisplay = document.getElementById('ai-answer');
            if (!answerDisplay) return;
            
            console.log('🌅 Starting gradual answer fade');
            this.updateInterviewStatus('🌅 Answer fading - will clear on next question');
            
            let opacity = 1;
            const fadeInterval = setInterval(() => {
                opacity -= 0.05;
                answerDisplay.style.opacity = Math.max(0.3, opacity);
                
                if (opacity <= 0.3) {
                    clearInterval(fadeInterval);
                    console.log('💡 Answer at minimum visibility - ready for next question');
                }
            }, 1000);
        }

        isInterviewQuestion(text) {
            const cleanText = text.toLowerCase().trim();
            
            const greetingPatterns = [
                /^(hi|hello|hey|good morning|good afternoon|good evening)/,
                /how are you/,
                /test/,
                /can you hear me/
            ];
            
            const questionPatterns = [
                /^(tell me about|describe|explain|what is|what are)/,
                /^(how do you|how would you|how did you)/,
                /^(why did you|why do you|why would you)/,
                /^(when did you|when do you|when would you)/,
                /^(where did you|where do you|where would you)/,
                /^(can you|could you|would you)/,
                /^(have you|did you|do you)/,
                /^(what's your experience|what is your experience)/,
                /^(give me an example|provide an example)/,
                /^(walk me through)/,
                /\?$/ // Ends with question mark
            ];
            
            const technicalTerms = [
                'api', 'database', 'python', 'javascript', 'react', 'node',
                'programming', 'coding', 'development', 'software', 'algorithm',
                'framework', 'library', 'microservices', 'architecture'
            ];
            
            const isGreeting = greetingPatterns.some(pattern => pattern.test(cleanText));
            const isQuestion = questionPatterns.some(pattern => pattern.test(cleanText));
            const hasTechTerms = technicalTerms.some(term => cleanText.includes(term));
            
            return isGreeting || isQuestion || hasTechTerms;
        }

        async getInterviewAIResponse(question) {
            try {
                console.log('🧠 Getting interview-optimized AI response for:', question);
                this.updateInterviewStatus('🧠 AI analyzing question...');
                
                const interviewPrompt = `You are helping someone during a live job interview. They were just asked: "${question}"

Please provide a concise, professional response that:
- Sounds natural and conversational
- Is appropriate for a job interview
- Shows confidence and competence
- Is brief but complete (2-3 sentences max)
- Avoids mentioning you're an AI
- Uses "I" statements as if the person is speaking

Context: This is a live interview situation where the person needs to respond professionally and confidently.`;

                const response = await fetch('http://localhost:8084/api/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        question: interviewPrompt,
                        interview_mode: true,
                        context: 'live_interview',
                        optimization: 'concise_professional',
                        max_tokens: 200,
                        temperature: 0.7
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('✅ Got interview AI response:', data.answer);
                    this.displayStealthInterviewAnswer(data.answer || data.response, question);
                    this.updateInterviewStatus('✅ Answer ready - Intelligent persistence active');
                } else {
                    console.error('❌ Interview AI API error:', response.status);
                    this.displayStealthInterviewAnswer('Sorry, I couldn\'t process that question right now. Could you please repeat it?', question);
                    this.updateInterviewStatus('❌ AI Error - Check connection');
                }
            } catch (error) {
                console.error('❌ Network error getting interview AI response:', error);
                this.displayStealthInterviewAnswer('Network connection issue - please check your internet connection.', question);
                this.updateInterviewStatus('❌ Connection Error');
            }
        }

        displayStealthInterviewAnswer(response, question) {
            console.log('🎯 Displaying stealth interview answer:', response);
            
            const questionDisplay = document.getElementById('current-question');
            const answerDisplay = document.getElementById('ai-answer');
            
            if (!questionDisplay || !answerDisplay) {
                console.warn('Stealth overlay elements not found');
                return;
            }
            
            // Reset answer state for new question
            this.interviewMode.answerState = {
                isDisplayed: true,
                userIsReading: false,
                readingStartTime: null,
                readingCompleted: false,
                lastActivity: Date.now()
            };
            
            // Only clear if this is a NEW question
            if (this.lastQuestion !== question) {
                questionDisplay.innerHTML = '';
                answerDisplay.innerHTML = '';
                answerDisplay.style.opacity = '1';
                answerDisplay.style.borderLeft = 'none';
                answerDisplay.style.backgroundColor = 'transparent';
                answerDisplay.style.display = 'block';
                
                // Clear timers
                if (this.answerPersistenceTimer) {
                    clearTimeout(this.answerPersistenceTimer);
                }
                if (this.answerFadeTimer) {
                    clearTimeout(this.answerFadeTimer);
                }
                
                this.lastQuestion = question;
            }
            
            // Show the question
            if (question) {
                questionDisplay.classList.add('active');
                questionDisplay.innerHTML = `<strong>❓ Question:</strong> ${question}`;
                questionDisplay.style.display = 'block';
            }
            
            // Optimize answer for interview context
            const interviewAnswer = this.optimizeAnswerForInterview(response, question);
            
            // Display answer with improved typing effect
            this.typewriterEffect(answerDisplay, interviewAnswer, () => {
                console.log('✅ Answer display complete - Intelligent persistence active');
                console.log('🧠 System will monitor user speech to keep answer visible while reading');
                this.setInitialAnswerPersistence();
            });
        }

        optimizeAnswerForInterview(rawResponse, question) {
            let answer = rawResponse;
            
            const questionLower = question ? question.toLowerCase() : '';
            const isGreeting = questionLower.includes('how are you') || questionLower.includes('hello') || questionLower.includes('hi ');
            const isAboutYou = questionLower.includes('tell me about yourself') || questionLower.includes('about you');
            const isTechnical = questionLower.includes('technical') || questionLower.includes('code') || questionLower.includes('programming');
            
            // Remove AI references
            answer = answer.replace(/As an AI|I'm an AI|As a language model|I'm a language model/gi, '');
            answer = answer.replace(/I don't have personal experience/gi, 'In my experience');
            answer = answer.replace(/I cannot|I can't/gi, 'Let me think about this differently');
            answer = answer.replace(/I don't have feelings/gi, 'I feel');
            
            // Handle specific interview question types
            if (isGreeting) {
                answer = "I'm doing great, thank you for asking! I'm excited about this opportunity and looking forward to our conversation. How are you doing today?";
            } else if (isAboutYou) {
                answer = "I'm a passionate professional with experience in software development and problem-solving. I enjoy taking on challenging projects and collaborating with teams to deliver innovative solutions. I'm particularly interested in this role because it aligns with my skills and career goals. What specific aspects of my background would you like me to elaborate on?";
            }
            
            // Shorten if too long
            if (answer.length > 400) {
                const sentences = answer.split('. ');
                let keyAnswer = sentences.slice(0, 3).join('. ') + '.';
                
                if (sentences.length > 3) {
                    keyAnswer += `\n\n💡 I can elaborate on:\n${sentences.slice(3, 6).map(s => `• ${s.trim()}`).join('\n')}`;
                }
                answer = keyAnswer;
            }
            
            // Add confident starters if needed
            const confidenceStarters = [
                "Based on my experience, ",
                "From my work with, ",
                "In my previous projects, ",
                "What I've found effective is ",
                "My approach has been to "
            ];
            
            if (!answer.match(/^(Based on|From my|In my|What I've|My approach|I'm)/i) && !isGreeting) {
                const starter = confidenceStarters[Math.floor(Math.random() * confidenceStarters.length)];
                answer = starter + answer.charAt(0).toLowerCase() + answer.slice(1);
            }
            
            if (isTechnical && !answer.includes('Would you like me to')) {
                answer += "\n\nWould you like me to elaborate on any specific aspect of this?";
            }
            
            return answer;
        }

        typewriterEffect(element, text, callback) {
            if (this.interviewMode.isTyping) {
                return;
            }
            
            this.interviewMode.isTyping = true;
            element.innerHTML = '';
            element.classList.add('typing-cursor');
            
            let index = 0;
            const baseTypingSpeed = 60; // Faster for better UX
            
            const typeChar = () => {
                if (index < text.length) {
                    const char = text.charAt(index);
                    
                    let delay = baseTypingSpeed;
                    if (char === '.' || char === '!' || char === '?') {
                        delay = baseTypingSpeed * 4;
                    } else if (char === ',' || char === ';') {
                        delay = baseTypingSpeed * 2;
                    } else if (char === '\n') {
                        delay = baseTypingSpeed * 3;
                    } else if (char === ' ') {
                        delay = baseTypingSpeed * 1.1;
                    }
                    
                    if (char === '\n') {
                        element.innerHTML += '<br>';
                    } else {
                        element.innerHTML += char;
                    }
                    
                    index++;
                    element.scrollTop = element.scrollHeight;
                    
                    setTimeout(typeChar, delay);
                } else {
                    element.classList.remove('typing-cursor');
                    this.interviewMode.isTyping = false;
                    
                    if (callback) callback();
                }
            };
            
            typeChar();
        }

        setInitialAnswerPersistence() {
            // Set initial persistence - minimum 60 seconds
            this.scheduleAnswerFade(60000); // 60 seconds initial persistence
            
            const answerDisplay = document.getElementById('ai-answer');
            if (answerDisplay) {
                answerDisplay.style.borderLeft = '3px solid #00ff00';
                answerDisplay.style.backgroundColor = 'rgba(0, 255, 0, 0.05)';
            }
            
            console.log('📌 Answer will stay visible for at least 60 seconds');
            console.log('🧠 Intelligent monitoring active - will extend if user is reading/responding');
        }

        showVoiceRecognitionWorking() {
            const statusEl = document.getElementById('ai-status');
            if (statusEl) {
                statusEl.innerHTML = '🎤 Voice Recognition Active';
                statusEl.style.color = '#00ff00';
            }
            
            // Show ready state in interview content
            const contentEl = document.getElementById('interview-content');
            if (contentEl && !document.getElementById('ai-answer').style.display) {
                contentEl.innerHTML = `
                    <div style="text-align: center; padding: 30px; color: #00ff00;">
                        <div style="font-size: 24px; margin-bottom: 15px;">🎤</div>
                        <div style="margin-bottom: 10px; font-weight: bold;">Ready for Interview Questions</div>
                        <div style="font-size: 10px;">
                            🧠 Intelligent persistence enabled<br>
                            📖 Detects when you're reading answers<br>
                            ⏰ Keeps answers visible until you're done<br>
                            🎯 Test: "Hi how are you" or "Tell me about yourself"
                        </div>
                    </div>
                `;
            }
        }

        showVoiceRecognitionFallback() {
            const statusEl = document.getElementById('ai-status');
            if (statusEl) {
                statusEl.innerHTML = '⚠️ Voice Recognition Not Available';
                statusEl.style.color = '#ff6b6b';
            }
            
            const contentEl = document.getElementById('interview-content');
            if (contentEl) {
                contentEl.innerHTML = `
                    <div style="text-align: center; padding: 30px; color: #ff6b6b;">
                        <div style="font-size: 24px; margin-bottom: 15px;">⚠️</div>
                        <div style="margin-bottom: 10px;">Voice Recognition Unavailable</div>
                        <div style="font-size: 10px;">
                            Please allow microphone access or<br>
                            use a supported browser (Chrome/Edge)
                        </div>
                    </div>
                `;
            }
        }

        monitorGeneric() {
            console.log('🔍 Starting generic platform monitoring');
            this.updateStatus('🔍 Monitoring generic platform');
        }

        updateStatus(status) {
            const statusEl = document.getElementById('ai-status');
            if (statusEl) {
                statusEl.textContent = status;
            }
            console.log('📊 Status:', status);
        }

        updateInterviewStatus(status) {
            this.updateStatus(status);
            const confidenceEl = document.getElementById('confidence-text');
            if (confidenceEl) {
                confidenceEl.textContent = status.includes('✅') ? 'Ready' : 
                                         status.includes('🧠') ? 'Think' :
                                         status.includes('📖') ? 'Read' :
                                         status.includes('⏰') ? 'Wait' : 'Listen';
            }
        }
    }

    // Initialize the assistant
    const assistant = new MeetingAIAssistant();
    
    // Make it globally accessible for debugging
    window.AIMentorAssistant = assistant;
    
    // Add test functions for debugging
    window.testVoice = function(text) {
        console.log('🧪 Testing voice input:', text);
        assistant.handleVoiceResult({
            resultIndex: 0,
            results: [{
                isFinal: true,
                0: { transcript: text }
            }]
        });
    };
    
    window.quickTests = {
        greeting: () => testVoice("Hi how are you"),
        about: () => testVoice("Tell me about yourself"),
        experience: () => testVoice("What is your experience with Python"),
        api: () => testVoice("How do you design APIs")
    };
    
    // Log available test functions
    setTimeout(() => {
        console.log('🧪 Test functions available:');
        console.log('- testVoice("your question")');
        console.log('- quickTests.greeting()');
        console.log('- quickTests.about()');
        console.log('- quickTests.experience()');
        console.log('- quickTests.api()');
        console.log('- Say "Hi how are you" or "Tell me about yourself" to test voice');
    }, 2000);

    console.log('✅ AI Mentor Content Script fully loaded with intelligent persistence');
}
