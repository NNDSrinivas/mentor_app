// Offscreen audio processing for AI Mentor Assistant
class AudioProcessor {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.speechRecognition = null;
        this.currentSpeaker = null;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        console.log('🎤 Audio processor initialized');
        this.setupSpeechRecognition();
        this.setupMessageListener();
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

// Initialize audio processor
const audioProcessor = new AudioProcessor();
