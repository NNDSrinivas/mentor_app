// Content script for meeting platforms - AI Interview Assistant
// Clean version with ultra-fast speech recognition and intelligent features

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
            this.lastQuestion = null;
            this.meetingData = {
                participants: [],
                chatHistory: [],
                jiraTickets: [],
                screenShareActive: false
            };
            
            // Enhanced speaker detection state
            this.speakerDetection = {
                userSpeaking: false,
                interviewerSpeaking: false,
                lastSpeechTime: 0,
                speechBuffer: '',
                silenceTimer: null,
                questionCompleteTimer: null,
                readingDetection: {
                    isReading: false,
                    readingStartTime: null,
                    currentLine: 0,
                    totalLines: 0,
                    readingSpeed: 200, // words per minute
                    autoScrollTimer: null
                },
                voicePatterns: {
                    userVoiceFingerprint: null,
                    interviewerVoiceFingerprint: null,
                    confidenceThreshold: 0.7
                }
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
                
                this.isActive = true;
                console.log('✅ AI Mentor initialized successfully');
            } catch (error) {
                console.error('❌ Failed to initialize AI Mentor:', error);
            }
        }

        createStealthInterviewOverlay() {
            // Remove existing overlay if present
            if (this.overlay) {
                this.overlay.remove();
            }

            // Create main overlay container
            this.overlay = document.createElement('div');
            this.overlay.id = 'ai-interview-stealth-overlay';
            
            // Add comprehensive CSS
            const style = document.createElement('style');
            style.textContent = `
                #ai-interview-stealth-overlay {
                    position: fixed !important;
                    top: 10px !important;
                    right: 10px !important;
                    width: 600px !important;
                    height: 800px !important;
                    background: rgba(0, 0, 0, 0.98) !important;
                    color: #00ff00 !important;
                    font-family: 'Courier New', monospace !important;
                    font-size: 12px !important;
                    z-index: 2147483647 !important;
                    border-radius: 15px !important;
                    border: 2px solid rgba(255, 107, 107, 0.8) !important;
                    backdrop-filter: blur(20px) !important;
                    box-shadow: 0 0 20px rgba(255, 107, 107, 0.7) !important;
                    user-select: none !important;
                    pointer-events: auto !important;
                    opacity: 0.95 !important;
                    visibility: visible !important;
                    display: block !important;
                    transform: scale(1) !important;
                    transition: all 0.3s ease !important;
                    overflow: hidden !important;
                }

                #ai-interview-stealth-overlay.screen-sharing {
                    opacity: 0 !important;
                    visibility: hidden !important;
                    transform: scale(0.8) translateX(100%) !important;
                    pointer-events: none !important;
                }

                .stealth-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 15px;
                    border-bottom: 1px solid rgba(0, 255, 0, 0.3);
                    background: rgba(255, 107, 107, 0.1);
                    cursor: move;
                }

                .stealth-title {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .stealth-controls {
                    display: flex;
                    gap: 8px;
                }

                .stealth-btn {
                    background: rgba(0, 255, 0, 0.2);
                    border: 1px solid #00ff00;
                    color: #00ff00;
                    padding: 4px 8px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 10px;
                    transition: all 0.2s;
                }

                .stealth-btn:hover {
                    background: rgba(0, 255, 0, 0.4);
                    transform: scale(1.05);
                }

                .stealth-content {
                    height: calc(100% - 60px);
                    padding: 15px;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }

                #question-display {
                    background: rgba(0, 100, 255, 0.1);
                    border-left: 3px solid #0066ff;
                    padding: 10px;
                    margin-bottom: 15px;
                    border-radius: 5px;
                    font-size: 11px;
                    max-height: 80px;
                    overflow-y: auto;
                    display: none;
                }

                #ai-answer {
                    flex: 1;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid #00ff00;
                    border-radius: 8px;
                    padding: 20px;
                    overflow-y: auto;
                    font-size: 13px;
                    line-height: 1.7;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }

                #status {
                    text-align: center;
                    padding: 10px;
                    border-top: 1px solid rgba(0, 255, 0, 0.3);
                    background: rgba(0, 0, 0, 0.5);
                    font-size: 11px;
                    color: #888;
                }

                #ai-answer::-webkit-scrollbar { width: 8px; }
                #ai-answer::-webkit-scrollbar-track { background: rgba(0, 255, 0, 0.1); }
                #ai-answer::-webkit-scrollbar-thumb { background: rgba(0, 255, 0, 0.6); border-radius: 4px; }
            `;
            
            document.head.appendChild(style);

            // Set up overlay HTML
            this.overlay.innerHTML = `
                <div class="stealth-header">
                    <div class="stealth-title">
                        <span style="font-size: 14px;">🤖</span>
                        <span>AI Interview Assistant</span>
                    </div>
                    <div class="stealth-controls">
                        <button class="stealth-btn" id="minimize-btn">−</button>
                        <button class="stealth-btn" id="close-btn">×</button>
                    </div>
                </div>
                <div class="stealth-content">
                    <div id="question-display"></div>
                    <div id="ai-answer">
                        <div style="text-align: center; padding: 30px; color: #888;">
                            <div style="font-size: 20px; margin-bottom: 15px;">🎤</div>
                            <div style="margin-bottom: 10px;">AI Interview Assistant Ready</div>
                            <div style="font-size: 10px;">
                                • Voice recognition active<br>
                                • Ultra-fast response mode<br>
                                • Intelligent speaker detection<br>
                                • Auto-scroll reading assistance
                            </div>
                        </div>
                    </div>
                </div>
                <div id="status">🔧 Initializing...</div>
            `;

            document.body.appendChild(this.overlay);
            
            // Set up drag functionality
            this.setupDragFunctionality();
            
            // Set up controls
            this.setupControls();
            
            console.log('✅ Stealth overlay created successfully');
        }

        setupDragFunctionality() {
            const header = this.overlay.querySelector('.stealth-header');
            let isDragging = false;
            let dragOffset = { x: 0, y: 0 };

            header.addEventListener('mousedown', (e) => {
                isDragging = true;
                const rect = this.overlay.getBoundingClientRect();
                dragOffset.x = e.clientX - rect.left;
                dragOffset.y = e.clientY - rect.top;
                header.style.cursor = 'grabbing';
            });

            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    e.preventDefault();
                    const x = e.clientX - dragOffset.x;
                    const y = e.clientY - dragOffset.y;
                    
                    // Keep within viewport bounds
                    const maxX = window.innerWidth - this.overlay.offsetWidth;
                    const maxY = window.innerHeight - this.overlay.offsetHeight;
                    
                    this.overlay.style.left = Math.max(0, Math.min(x, maxX)) + 'px';
                    this.overlay.style.top = Math.max(0, Math.min(y, maxY)) + 'px';
                    this.overlay.style.right = 'auto';
                }
            });

            document.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    header.style.cursor = 'move';
                }
            });
        }

        setupControls() {
            const minimizeBtn = this.overlay.querySelector('#minimize-btn');
            const closeBtn = this.overlay.querySelector('#close-btn');

            minimizeBtn.addEventListener('click', () => {
                const content = this.overlay.querySelector('.stealth-content');
                if (content.style.display === 'none') {
                    content.style.display = 'flex';
                    this.overlay.style.height = '800px';
                    minimizeBtn.textContent = '−';
                } else {
                    content.style.display = 'none';
                    this.overlay.style.height = '60px';
                    minimizeBtn.textContent = '+';
                }
            });

            closeBtn.addEventListener('click', () => {
                this.overlay.style.display = 'none';
            });
        }

        async connectToAI() {
            try {
                console.log('🔗 Connecting to AI service...');
                const response = await fetch('http://localhost:8084/api/health');
                if (response.ok) {
                    this.updateStatus('🤖 AI Connected - Voice recognition ready');
                    console.log('✅ Connected to AI service');
                } else {
                    this.updateStatus('❌ AI Offline - Start mentor app');
                    console.log('❌ AI service offline');
                }
            } catch (error) {
                this.updateStatus('❌ AI Offline - Start mentor app');
                console.error('❌ Failed to connect to AI:', error);
            }
        }

        startMeetingMonitoring() {
            if (!this.isActive) return;
            
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
                this.updateStatus('❌ Microphone access denied - Manual mode only');
            }
        }

        async initializeSpeechRecognition() {
            console.log('🎤 Setting up ULTRA-FAST speech recognition with speaker detection...');
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                console.error('❌ Speech recognition not supported');
                this.updateStatus('❌ Speech recognition not supported');
                return;
            }

            try {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.recognition = new SpeechRecognition();
                
                // ULTRA-FAST configuration for real-time processing
                this.recognition.continuous = true;
                this.recognition.interimResults = true;
                this.recognition.maxAlternatives = 3;
                this.recognition.lang = 'en-US';
                
                let restartTimeout;
                
                this.recognition.onstart = () => {
                    console.log('🎤 Voice recognition started - ready to listen');
                    this.updateStatus('🎤 Listening for questions...');
                };
                
                this.recognition.onresult = (event) => {
                    this.handleVoiceResultFast(event);
                };
                
                this.recognition.onerror = (event) => {
                    console.log('🎤 Voice recognition event:', event.error);
                    
                    if (event.error === 'not-allowed') {
                        this.updateStatus('❌ Microphone permission denied');
                        return;
                    }
                    
                    if (event.error === 'no-speech' || event.error === 'audio-capture') {
                        console.log('🔇 No speech detected - this is normal, continuing to listen...');
                        this.updateStatus('🎤 Listening... (no speech detected yet)');
                        return;
                    }
                    
                    if (event.error === 'network') {
                        console.log('🌐 Network error in speech recognition, will retry...');
                        this.updateStatus('⚠️ Network issue - retrying...');
                    } else {
                        console.error('🎤 Voice recognition error:', event.error);
                        this.updateStatus(`⚠️ Voice error: ${event.error} - Restarting...`);
                    }
                    
                    clearTimeout(restartTimeout);
                    restartTimeout = setTimeout(() => {
                        console.log('🔄 Restarting voice recognition...');
                        if (this.recognition) {
                            try {
                                this.recognition.start();
                            } catch (e) {
                                console.log('🔄 Recognition already running, continuing...');
                            }
                        }
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
                this.updateStatus('❌ Speech recognition failed');
            }
        }

        handleVoiceResultFast(event) {
            let interimTranscript = '';
            let finalTranscript = '';
            
            // Process all results for immediate feedback
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                const confidence = event.results[i][0].confidence;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            const currentText = finalTranscript || interimTranscript;
            if (!currentText.trim()) return;
            
            // FAST speaker detection using voice patterns and timing
            const now = Date.now();
            const timeSinceLastSpeech = now - this.speakerDetection.lastSpeechTime;
            
            // Determine who is speaking based on patterns
            const speaker = this.identifySpeaker(currentText, timeSinceLastSpeech, event.results[event.resultIndex][0].confidence);
            
            if (speaker === 'interviewer') {
                this.handleInterviewerSpeech(currentText, finalTranscript);
            } else {
                this.handleUserSpeech(currentText, finalTranscript);
            }
            
            this.speakerDetection.lastSpeechTime = now;
            this.speakerDetection.speechBuffer = currentText;
        }

        identifySpeaker(text, timeSinceLastSpeech, confidence) {
            // Fast speaker identification using multiple signals
            
            // 1. Question patterns (high probability interviewer)
            const questionPatterns = [
                'tell me about', 'what is your', 'how would you', 'can you explain',
                'what are your', 'describe', 'why did you', 'how do you',
                'what would you do', 'walk me through', 'what is the difference',
                'how would you handle', 'what challenges', 'give me an example'
            ];
            
            const isQuestionLike = questionPatterns.some(pattern => 
                text.toLowerCase().includes(pattern)
            ) || text.trim().endsWith('?');
            
            // 2. Response patterns (high probability user)
            const responsePatterns = [
                'so ', 'well ', 'i think', 'in my experience', 'i would',
                'basically', 'actually', 'essentially', 'i believe',
                'from my perspective', 'i have worked', 'i used'
            ];
            
            const isResponseLike = responsePatterns.some(pattern =>
                text.toLowerCase().startsWith(pattern)
            );
            
            // 3. Context awareness
            const hasActiveAnswer = this.speakerDetection.readingDetection.isReading;
            
            // Fast decision logic
            if (isQuestionLike && !hasActiveAnswer) {
                return 'interviewer';
            }
            
            if (isResponseLike || hasActiveAnswer) {
                return 'user';
            }
            
            // Default based on timing and patterns
            if (timeSinceLastSpeech > 3000) {
                return 'interviewer'; // New conversation after silence
            }
            
            return this.speakerDetection.interviewerSpeaking ? 'interviewer' : 'user';
        }

        handleInterviewerSpeech(currentText, finalTranscript) {
            this.speakerDetection.interviewerSpeaking = true;
            this.speakerDetection.userSpeaking = false;
            
            // Clear any reading state
            this.speakerDetection.readingDetection.isReading = false;
            
            // If we have final transcript, process immediately
            if (finalTranscript.trim()) {
                console.log('🎯 Interviewer asked:', finalTranscript);
                this.processInterviewQuestion(finalTranscript);
            } else {
                // Show interim question
                console.log('👂 Interviewer speaking:', currentText);
                this.showInterimQuestion(currentText);
            }
        }

        handleUserSpeech(currentText, finalTranscript) {
            this.speakerDetection.userSpeaking = true;
            this.speakerDetection.interviewerSpeaking = false;
            
            // If user is reading back an answer, enable auto-scroll
            if (this.speakerDetection.readingDetection.isReading) {
                this.handleAutoScroll(currentText);
            } else {
                // Check if user started reading an answer
                const answerDisplay = document.getElementById('ai-answer');
                if (answerDisplay && answerDisplay.style.display !== 'none') {
                    this.startReadingDetection(currentText);
                }
            }
            
            console.log('👤 User speaking:', currentText);
        }

        processInterviewQuestion(question) {
            // ULTRA-FAST question processing
            this.updateStatus('🧠 Generating answer...');
            this.getInterviewAIResponse(question);
        }

        showInterimQuestion(text) {
            const questionDisplay = document.getElementById('question-display');
            if (questionDisplay) {
                questionDisplay.style.display = 'block';
                questionDisplay.textContent = `🎯 ${text}`;
            }
        }

        startReadingDetection(userText) {
            const answerDisplay = document.getElementById('ai-answer');
            if (!answerDisplay) return;
            
            // Check if user is reading from the answer
            const answerText = answerDisplay.textContent.toLowerCase();
            const userTextLower = userText.toLowerCase();
            
            const words = userTextLower.split(' ');
            let matchCount = 0;
            
            words.forEach(word => {
                if (word.length > 3 && answerText.includes(word)) {
                    matchCount++;
                }
            });
            
            const matchRatio = matchCount / Math.max(words.length, 1);
            
            if (matchRatio > 0.4) { // 40% match threshold
                console.log('📖 Reading detection: User started reading answer');
                this.speakerDetection.readingDetection.isReading = true;
                this.speakerDetection.readingDetection.readingStartTime = Date.now();
                this.startAutoScroll();
            }
        }

        startAutoScroll() {
            const answerDisplay = document.getElementById('ai-answer');
            if (!answerDisplay) return;
            
            console.log('🔄 AUTO-SCROLL: Started intelligent scrolling');
            
            // Clear existing timer
            clearInterval(this.speakerDetection.readingDetection.autoScrollTimer);
            
            // Calculate scroll speed based on reading pace
            const wordsPerMinute = this.speakerDetection.readingDetection.readingSpeed;
            const scrollInterval = 60000 / (wordsPerMinute / 10); // Scroll every ~6 words
            
            this.speakerDetection.readingDetection.autoScrollTimer = setInterval(() => {
                if (this.speakerDetection.readingDetection.isReading) {
                    // Smooth auto-scroll
                    answerDisplay.scrollTop += 20;
                    
                    // Stop if reached bottom
                    if (answerDisplay.scrollTop >= answerDisplay.scrollHeight - answerDisplay.clientHeight) {
                        this.stopAutoScroll();
                    }
                } else {
                    this.stopAutoScroll();
                }
            }, scrollInterval);
        }

        handleAutoScroll(currentText) {
            // Adjust scroll speed based on user's speaking pace
            const words = currentText.split(' ').length;
            const timeSinceStart = Date.now() - this.speakerDetection.readingDetection.readingStartTime;
            
            if (timeSinceStart > 1000) { // After 1 second
                const currentWPM = (words / timeSinceStart) * 60000;
                this.speakerDetection.readingDetection.readingSpeed = Math.max(100, Math.min(300, currentWPM));
                
                console.log(`📊 Reading speed adjusted: ${Math.round(currentWPM)} WPM`);
            }
        }

        stopAutoScroll() {
            console.log('⏹️ AUTO-SCROLL: Stopped');
            clearInterval(this.speakerDetection.readingDetection.autoScrollTimer);
            this.speakerDetection.readingDetection.isReading = false;
        }

        async getInterviewAIResponse(question) {
            try {
                console.log('⚡ FAST: Getting AI response for:', question);
                this.updateStatus('⚡ Generating instant answer...');
                
                // FAST request - minimal overhead
                const requestBody = {
                    question: question,
                    interview_mode: true,
                    fast_mode: true,
                    context: 'technical_interview',
                    optimization: 'speed_and_accuracy',
                    interview_level: 'IC6_IC7_E5_E6_E7',
                    requirements: {
                        depth: 'professional_level',
                        include_examples: true,
                        include_code_samples: false,
                        response_length: 'concise_but_complete',
                        prioritize_speed: true
                    },
                    temperature: 0.2,
                    max_tokens: 800
                };

                const startTime = Date.now();

                const response = await fetch('http://localhost:8084/api/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestBody)
                });

                if (response.ok) {
                    const data = await response.json();
                    const responseTime = Date.now() - startTime;
                    
                    console.log(`⚡ FAST: Got response in ${responseTime}ms`);
                    this.displayAnswerWithSmartScroll(data.response, question, responseTime);
                    
                } else {
                    console.error('❌ FAST: API error:', response.status);
                    this.showFallbackResponse(question);
                }

            } catch (error) {
                console.error('❌ FAST: Network error:', error);
                this.showFallbackResponse(question);
            }
        }

        displayAnswerWithSmartScroll(answer, question, responseTime) {
            const answerDisplay = document.getElementById('ai-answer');
            const questionDisplay = document.getElementById('question-display');
            
            if (answerDisplay) {
                // Clear previous content
                answerDisplay.innerHTML = '';
                answerDisplay.scrollTop = 0;
                
                // Show question
                if (questionDisplay) {
                    questionDisplay.style.display = 'block';
                    questionDisplay.innerHTML = `<strong>🎯 Question:</strong> ${question}`;
                }
                
                // Display answer with typing effect for immediate feedback
                this.typeAnswer(answerDisplay, answer, responseTime);
                
                this.updateStatus(`✅ Answer ready (${responseTime}ms) - Reading assistance active`);
            }
        }

        typeAnswer(element, text, responseTime) {
            element.innerHTML = `<div style="color: #888; font-size: 10px; margin-bottom: 10px;">⚡ Response time: ${responseTime}ms | 🤖 AI Assistant</div>`;
            
            let index = 0;
            const speed = 20; // milliseconds between characters
            
            const typeChar = () => {
                if (index < text.length) {
                    if (index === 0) {
                        element.innerHTML += text.charAt(index);
                    } else {
                        element.innerHTML += text.charAt(index);
                    }
                    index++;
                    setTimeout(typeChar, speed);
                } else {
                    // Finished typing
                    console.log('✅ Answer display complete');
                    element.innerHTML += `<div style="color: #888; font-size: 10px; margin-top: 15px;">📖 Reading assistance: Start speaking to auto-scroll</div>`;
                }
            };
            
            typeChar();
        }

        showFallbackResponse(question) {
            const answerDisplay = document.getElementById('ai-answer');
            if (answerDisplay) {
                answerDisplay.innerHTML = `
                    <div style="text-align: center; color: #ff6b6b; padding: 30px;">
                        <div style="font-size: 16px; margin-bottom: 10px;">⚠️ AI Service Unavailable</div>
                        <div style="font-size: 12px; margin-bottom: 15px;">Question: ${question}</div>
                        <div style="font-size: 11px; color: #888;">
                            • Check if mentor app is running<br>
                            • Verify connection to localhost:8084<br>
                            • Try reloading the page
                        </div>
                    </div>
                `;
            }
            this.updateStatus('❌ AI service offline - Check mentor app');
        }

        updateStatus(message) {
            const statusElement = document.getElementById('status');
            if (statusElement) {
                statusElement.textContent = message;
            }
        }
    }

    // Initialize the AI assistant
    const aiAssistant = new MeetingAIAssistant();
    window.aiAssistant = aiAssistant;

    // Test functions for debugging
    window.testVoice = function(question) {
        console.log('🧪 Testing with question:', question);
        aiAssistant.getInterviewAIResponse(question);
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

    console.log('✅ AI Mentor Content Script fully loaded with ultra-fast performance');
}
