// Offscreen audio processing and stealth UI for AI Interview Assistant
class StealthInterviewAssistant {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.speechRecognition = null;
        this.currentSpeaker = null;
        this.conversationHistory = [];
        this.stealthUI = null;
        this.currentQuestion = '';
        this.currentAnswer = '';
        this.interviewLevel = 'IC6';
        this.targetCompany = null;
        this.init();
    }

    init() {
        console.log('🕵️ Stealth Interview Assistant initialized in offscreen');
        this.createStealthUI();
        this.setupSpeechRecognition();
        this.setupMessageListener();
    }

    createStealthUI() {
        console.log('🎨 Creating offscreen stealth UI...');
        
        // Create stealth interface that screen capture cannot see
        this.stealthUI = document.createElement('div');
        this.stealthUI.id = 'offscreen-interview-assistant';
        this.stealthUI.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 500px;
            height: 700px;
            background: rgba(0, 0, 0, 0.95);
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            border: 2px solid #00ff00;
            border-radius: 10px;
            padding: 15px;
            z-index: 999999;
            display: none;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        `;
        
        this.stealthUI.innerHTML = `
            <div style="border-bottom: 1px solid #00ff00; padding-bottom: 10px; margin-bottom: 15px;">
                <h2 style="margin: 0; color: #00ff00; text-align: center;">🕵️ STEALTH INTERVIEW ASSISTANT</h2>
                <div style="text-align: center; font-size: 10px; color: #888; margin-top: 5px;">
                    Hidden from screen capture - Only visible to YOU
                </div>
            </div>
            
            <div id="interview-config" style="margin-bottom: 15px; border-bottom: 1px solid rgba(0, 255, 0, 0.3); padding-bottom: 10px;">
                <div style="margin-bottom: 8px;">
                    <label style="font-size: 10px; color: #888;">Interview Level:</label>
                    <select id="stealth-level-select" style="width: 100%; padding: 5px; background: #000; color: #00ff00; border: 1px solid #00ff00; margin-top: 3px;">
                        <option value="IC5">IC5 - Software Engineer</option>
                        <option value="IC6" selected>IC6 - Senior Software Engineer</option>
                        <option value="IC7">IC7 - Staff Software Engineer</option>
                        <option value="E5">E5 - Senior Engineer (Meta)</option>
                        <option value="E6">E6 - Staff Engineer (Meta)</option>
                        <option value="E7">E7 - Senior Staff Engineer (Meta)</option>
                    </select>
                </div>
                <div>
                    <label style="font-size: 10px; color: #888;">Target Company:</label>
                    <select id="stealth-company-select" style="width: 100%; padding: 5px; background: #000; color: #00ff00; border: 1px solid #00ff00; margin-top: 3px;">
                        <option value="">Select Company (Optional)</option>
                        <option value="Meta">Meta</option>
                        <option value="Google">Google</option>
                        <option value="Amazon">Amazon</option>
                        <option value="Microsoft">Microsoft</option>
                        <option value="Apple">Apple</option>
                        <option value="Netflix">Netflix</option>
                    </select>
                </div>
            </div>
            
            <div id="question-section" style="margin-bottom: 15px; display: none;">
                <div style="font-size: 11px; color: #0066ff; margin-bottom: 5px;">📝 Current Question:</div>
                <div id="current-question-display" style="background: rgba(0, 100, 255, 0.1); padding: 8px; border-radius: 5px; border-left: 3px solid #0066ff; font-size: 11px; max-height: 60px; overflow-y: auto;"></div>
            </div>
            
            <div id="answer-section" style="flex: 1;">
                <div style="font-size: 11px; color: #00ff00; margin-bottom: 5px;">🤖 AI Response:</div>
                <div id="ai-response-display" style="background: rgba(0, 0, 0, 0.5); padding: 15px; border-radius: 5px; border: 1px solid #00ff00; height: 450px; overflow-y: auto; font-size: 12px; line-height: 1.6; white-space: pre-wrap;">
                    <div style="text-align: center; color: #888; padding: 50px 20px;">
                        <div style="font-size: 24px; margin-bottom: 15px;">🎤</div>
                        <div>Offscreen Stealth Mode Active</div>
                        <div style="font-size: 10px; margin-top: 10px;">
                            • Completely invisible to screen sharing<br>
                            • Voice recognition active<br>
                            • Ready for interview questions<br>
                            • Test: "Tell me about yourself"
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 10px; border-top: 1px solid rgba(0, 255, 0, 0.3); padding-top: 10px;">
                <input type="text" id="manual-question-offscreen" placeholder="Type question to test..." 
                       style="width: 70%; padding: 8px; background: #000; border: 1px solid #00ff00; color: #00ff00; margin-right: 5px;">
                <button id="test-question-btn" style="padding: 8px 12px; background: #00ff00; color: #000; border: none; cursor: pointer;">Test</button>
            </div>
        `;
        
        document.body.appendChild(this.stealthUI);
        this.setupStealthUIHandlers();
        
        console.log('✅ Offscreen stealth UI created');
    }

    setupStealthUIHandlers() {
        const levelSelect = document.getElementById('stealth-level-select');
        const companySelect = document.getElementById('stealth-company-select');
        const testBtn = document.getElementById('test-question-btn');
        const questionInput = document.getElementById('manual-question-offscreen');
        
        if (levelSelect) {
            levelSelect.addEventListener('change', (e) => {
                this.updateInterviewConfig(e.target.value, companySelect?.value);
            });
        }
        
        if (companySelect) {
            companySelect.addEventListener('change', (e) => {
                this.updateInterviewConfig(levelSelect?.value, e.target.value);
            });
        }
        
        if (testBtn && questionInput) {
            const testQuestion = () => {
                const question = questionInput.value.trim();
                if (question) {
                    this.processTestQuestion(question);
                    questionInput.value = '';
                }
            };
            
            testBtn.addEventListener('click', testQuestion);
            questionInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') testQuestion();
            });
        }
        
        console.log('✅ Stealth UI handlers setup complete');
    }

    showStealthUI() {
        if (this.stealthUI) {
            this.stealthUI.style.display = 'block';
            console.log('👁️ Stealth UI now visible (offscreen only)');
        }
    }

    hideStealthUI() {
        if (this.stealthUI) {
            this.stealthUI.style.display = 'none';
            console.log('🫥 Stealth UI hidden');
        }
    }

    updateInterviewConfig(level, company) {
        this.interviewLevel = level || 'IC6';
        this.targetCompany = company || null;
        
        console.log(`🎯 Interview config updated: ${this.interviewLevel}${company ? ' at ' + company : ''}`);
        
        // Notify main content script
        chrome.runtime.sendMessage({
            action: 'updateInterviewConfig',
            level: this.interviewLevel,
            company: this.targetCompany
        });
    }

    async processTestQuestion(question) {
        this.displayQuestion(question);
        await this.getAIResponse(question);
    }

    displayQuestion(question) {
        this.currentQuestion = question;
        const questionSection = document.getElementById('question-section');
        const questionDisplay = document.getElementById('current-question-display');
        
        if (questionSection && questionDisplay) {
            questionDisplay.textContent = question;
            questionSection.style.display = 'block';
        }
        
        console.log('📝 Question displayed:', question);
    }

    async getAIResponse(question) {
        try {
            const answerDisplay = document.getElementById('ai-response-display');
            if (answerDisplay) {
                answerDisplay.innerHTML = '<div style="text-align: center; color: #888;">🤔 Thinking...</div>';
            }
            
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: question,
                    context: {
                        type: 'personalized_interview_response',
                        interview_level: this.interviewLevel,
                        target_company: this.targetCompany,
                        mode: 'stealth_interview',
                        use_profile: true
                    }
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.displayAnswer(data.answer);
                console.log('✅ AI response received in stealth mode');
            } else {
                throw new Error('Failed to get AI response');
            }
        } catch (error) {
            console.error('❌ Error getting AI response:', error);
            const answerDisplay = document.getElementById('ai-response-display');
            if (answerDisplay) {
                answerDisplay.innerHTML = '<div style="color: #ff6b6b;">❌ Error: Could not connect to AI service. Make sure the mentor app is running.</div>';
            }
        }
    }

    displayAnswer(answer) {
        const answerDisplay = document.getElementById('ai-response-display');
        if (answerDisplay) {
            // Type out the answer with a typewriter effect
            answerDisplay.innerHTML = '';
            this.typeAnswer(answerDisplay, answer);
        }
    }

    typeAnswer(element, text, index = 0) {
        if (index < text.length) {
            element.textContent += text.charAt(index);
            element.scrollTop = element.scrollHeight;
            setTimeout(() => this.typeAnswer(element, text, index + 1), 30);
        }
    }

    setupSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            
            this.speechRecognition.continuous = true;
            this.speechRecognition.interimResults = true;
            this.speechRecognition.lang = 'en-US';
            
            this.speechRecognition.onresult = (event) => {
                this.processSpeechResult(event);
            };
            
            this.speechRecognition.onerror = (event) => {
                console.error('🎤 Speech recognition error:', event.error);
            };
            
            console.log('✅ Speech recognition ready in offscreen');
        } else {
            console.error('❌ Speech recognition not supported');
        }
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            switch (message.action) {
                case 'showStealthUI':
                    this.showStealthUI();
                    sendResponse({ success: true });
                    break;
                case 'hideStealthUI':
                    this.hideStealthUI();
                    sendResponse({ success: true });
                    break;
                case 'processQuestion':
                    this.processTestQuestion(message.question);
                    sendResponse({ success: true });
                    break;
                case 'updateConfig':
                    this.updateInterviewConfig(message.level, message.company);
                    sendResponse({ success: true });
                    break;
                case 'startRecording':
                    this.startRecording();
                    sendResponse({ success: true });
                    break;
                case 'stopRecording':
                    this.stopRecording();
                    sendResponse({ success: true });
                    break;
                case 'startSpeechRecognition':
                    this.startSpeechRecognition();
                    sendResponse({ success: true });
                    break;
                case 'stopSpeechRecognition':
                    this.stopSpeechRecognition();
                    sendResponse({ success: true });
                    break;
                default:
                    sendResponse({ success: false, error: 'Unknown action' });
            }
        });
        
        console.log('✅ Message listener setup complete');
    }

    async startRecording() {
        try {
            if (this.isRecording) return;
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.processAudioChunk(audioBlob);
            };
            
            this.mediaRecorder.start(1000); // Collect audio every second
            this.isRecording = true;
            
            console.log('🎤 Recording started in offscreen');
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;
            console.log('🛑 Recording stopped');
        }
    }

    startSpeechRecognition() {
        if (this.speechRecognition && !this.speechRecognition.continuous) {
            try {
                this.speechRecognition.start();
                console.log('🎤 Speech recognition started in offscreen');
            } catch (error) {
                console.error('❌ Failed to start speech recognition:', error);
            }
        }
    }

    stopSpeechRecognition() {
        if (this.speechRecognition) {
            this.speechRecognition.stop();
            console.log('🛑 Speech recognition stopped');
        }
    }

    processSpeechResult(event) {
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            }
        }
        
        if (finalTranscript.trim()) {
            console.log('🎤 Offscreen transcript:', finalTranscript);
            
            // Check if this looks like an interview question
            if (this.isInterviewQuestion(finalTranscript)) {
                this.processTestQuestion(finalTranscript);
            }
            
            // Also send to main content script
            chrome.runtime.sendMessage({
                action: 'speechResult',
                transcript: finalTranscript,
                source: 'offscreen'
            });
        }
    }

    isInterviewQuestion(text) {
        const questionWords = [
            'tell me about', 'describe', 'explain', 'how would you',
            'what is', 'why', 'when', 'where', 'how', 'can you',
            'have you ever', 'what\'s your experience', 'walk me through'
        ];
        
        const lowerText = text.toLowerCase();
        return questionWords.some(word => lowerText.includes(word)) || 
               lowerText.includes('?') ||
               lowerText.length > 20; // Assume longer statements might be questions
    }

    setupSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            
            this.speechRecognition.continuous = true;
            this.speechRecognition.interimResults = true;
            this.speechRecognition.lang = 'en-US';
            
            this.speechRecognition.onresult = (event) => {
                this.processSpeechResult(event);
            };
            
            this.speechRecognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
            };
            
            console.log('✅ Speech recognition ready');
        } else {
            console.error('❌ Speech recognition not supported');
        }
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            switch (message.action) {
                case 'startRecording':
                    this.startRecording();
                    sendResponse({ success: true });
                    break;
                case 'stopRecording':
                    this.stopRecording();
                    sendResponse({ success: true });
                    break;
                case 'getTranscription':
                    sendResponse({ 
                        success: true, 
                        data: this.conversationHistory 
                    });
                    break;
                default:
                    sendResponse({ success: false, error: 'Unknown action' });
            }
        });
    }

    async startRecording() {
        try {
            // Get screen and audio
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: 'screen' },
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    sampleRate: 44100
                }
            });

            // Setup media recorder for audio
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                    this.processAudioChunk(event.data);
                }
            };

            this.mediaRecorder.start(1000); // Collect data every second
            this.speechRecognition.start();
            this.isRecording = true;

            console.log('🎬 Recording started');
            
            // Notify background script
            chrome.runtime.sendMessage({
                action: 'recordingStarted',
                timestamp: new Date().toISOString()
            });

        } catch (error) {
            console.error('❌ Failed to start recording:', error);
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.speechRecognition.stop();
            this.isRecording = false;
            
            console.log('⏹️ Recording stopped');
            
            // Notify background script
            chrome.runtime.sendMessage({
                action: 'recordingStopped',
                audioData: this.audioChunks,
                conversation: this.conversationHistory,
                timestamp: new Date().toISOString()
            });
        }
    }

    processSpeechResult(event) {
        const results = event.results;
        const lastResult = results[results.length - 1];
        
        if (lastResult.isFinal) {
            const transcript = lastResult[0].transcript.trim();
            if (transcript.length > 0) {
                this.addToConversation(transcript);
            }
        }
    }

    addToConversation(transcript) {
        // Simple speaker identification (you can enhance this)
        const speakerType = this.identifySpeaker(transcript);
        
        const entry = {
            timestamp: new Date().toISOString(),
            speaker: speakerType,
            text: transcript,
            confidence: 0.8 // You can calculate actual confidence
        };

        this.conversationHistory.push(entry);
        
        // Send to background for AI processing
        chrome.runtime.sendMessage({
            action: 'newTranscription',
            data: entry
        });

        console.log(`👤 ${speakerType}: ${transcript}`);
    }

    identifySpeaker(transcript) {
        // Enhanced speaker identification
        // You can improve this with voice analysis or ML models
        
        // Simple heuristics for now
        if (transcript.toLowerCase().includes('i think') || 
            transcript.toLowerCase().includes('my opinion') ||
            transcript.toLowerCase().includes('let me')) {
            return 'user';
        } else if (transcript.toLowerCase().includes('what do you think') ||
                  transcript.toLowerCase().includes('can you') ||
                  transcript.toLowerCase().includes('please')) {
            return 'interviewer';
        } else {
            return 'other';
        }
    }

    async processAudioChunk(audioData) {
        // Send audio chunk for more detailed analysis if needed
        // This could be enhanced with voice fingerprinting
        const audioBuffer = await audioData.arrayBuffer();
        
        // You can add audio analysis here
        // For now, we rely on speech recognition
    }
}

// Initialize stealth interview assistant
const stealthAssistant = new StealthInterviewAssistant();
