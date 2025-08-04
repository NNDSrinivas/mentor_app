// Background script for AI Mentor Assistant
console.log('🚀 AI Mentor Background Script Loading...');

// Add error handler for the background script
self.addEventListener('error', (event) => {
    console.error('❌ Background script error:', event.error);
});

class MeetingDetector {
  constructor() {
    console.log('🎯 MeetingDetector initializing...');
    this.isRecording = false;
    this.currentMeeting = null;
    
    // Listen for tab updates to detect meeting platforms
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === 'complete') {
        this.checkForMeeting(tab);
      }
    });
    
    // Listen for messages from content scripts
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      this.handleMessage(message, sender, sendResponse);
    });
  }
  
  checkForMeeting(tab) {
    const meetingPatterns = [
      /meet\.google\.com\/[a-z0-9-]+/,
      /teams\.microsoft\.com.*meetup-join/,
      /zoom\.us\/j\/\d+/,
      /.*\.zoom\.us\/j\/\d+/
    ];
    
    const isMeetingUrl = meetingPatterns.some(pattern => 
      pattern.test(tab.url)
    );
    
    if (isMeetingUrl && !this.isRecording) {
      this.startMeetingDetection(tab);
    }
  }
  
  async startMeetingDetection(tab) {
    console.log('🎤 Meeting detected, starting AI Mentor Assistant');
    
    // Inject content script to detect meeting start/end
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
      });
      
      // Notify the AI Mentor backend
      this.notifyBackend('meeting_detected', {
        url: tab.url,
        title: tab.title,
        timestamp: Date.now()
      });
      
    } catch (error) {
      console.error('Failed to inject content script:', error);
    }
  }
  
  handleMessage(message, sender, sendResponse) {
    switch (message.type) {
      case 'meeting_started':
        this.onMeetingStarted(message.data);
        break;
      
      case 'meeting_ended':
        this.onMeetingEnded(message.data);
        break;
      
      case 'participant_speaking':
        this.onParticipantSpeaking(message.data);
        break;
        
      case 'screen_shared':
        this.onScreenShared(message.data);
        break;
    }
  }
  
  onMeetingStarted(data) {
    console.log('📞 Meeting started:', data);
    this.isRecording = true;
    this.currentMeeting = {
      id: this.generateMeetingId(),
      startTime: Date.now(),
      platform: this.detectPlatform(data.url),
      ...data
    };
    
    this.notifyBackend('start_recording', this.currentMeeting);
    this.updateBadge('REC');
  }
  
  onMeetingEnded(data) {
    console.log('📞 Meeting ended:', data);
    this.isRecording = false;
    
    if (this.currentMeeting) {
      this.currentMeeting.endTime = Date.now();
      this.currentMeeting.duration = this.currentMeeting.endTime - this.currentMeeting.startTime;
      
      this.notifyBackend('stop_recording', this.currentMeeting);
      this.currentMeeting = null;
    }
    
    this.updateBadge('');
  }
  
  onParticipantSpeaking(data) {
    // Track who's speaking for better transcription
    if (this.currentMeeting) {
      this.notifyBackend('speaker_change', {
        meetingId: this.currentMeeting.id,
        speaker: data.speaker,
        timestamp: Date.now()
      });
    }
  }
  
  onScreenShared(data) {
    // Capture screen sharing events
    if (this.currentMeeting) {
      this.notifyBackend('screen_shared', {
        meetingId: this.currentMeeting.id,
        sharedBy: data.sharedBy,
        timestamp: Date.now()
      });
    }
  }
  
  async notifyBackend(action, data) {
    try {
      // Send to local AI Mentor Assistant backend
      const response = await fetch('http://localhost:8084/api/meeting-events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action,
          data,
          timestamp: Date.now()
        })
      });
      
      if (!response.ok) {
        console.warn('Backend notification failed:', response.status);
      }
    } catch (error) {
      console.warn('Backend not available:', error.message);
      // Store events locally for later processing
      this.storeEventLocally(action, data);
    }
  }
  
  async storeEventLocally(action, data) {
    const events = await this.getStoredEvents();
    events.push({
      action,
      data,
      timestamp: Date.now()
    });
    
    await chrome.storage.local.set({
      pendingEvents: events.slice(-100) // Keep last 100 events
    });
  }
  
  async getStoredEvents() {
    const result = await chrome.storage.local.get(['pendingEvents']);
    return result.pendingEvents || [];
  }
  
  detectPlatform(url) {
    if (url.includes('meet.google.com')) return 'google_meet';
    if (url.includes('teams.microsoft.com')) return 'microsoft_teams';
    if (url.includes('zoom.us')) return 'zoom';
    return 'unknown';
  }
  
  generateMeetingId() {
    return 'meeting_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }
  
  updateBadge(text) {
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color: text ? '#ff4444' : '#00ff00' });
  }
}

// Background service worker for AI Meeting Mentor Extension
class BackgroundService {
    constructor() {
        this.init();
    }

    init() {
        this.setupMessageListeners();
        this.setupTabListeners();
        this.setupAlarms();
        this.setupOffscreenDocument();
        // Perform initial health check
        this.performHealthCheck();
        console.log('🤖 AI Meeting Mentor background service initialized');
    }

    async setupOffscreenDocument() {
        try {
            // Create offscreen document for audio processing
            await chrome.offscreen.createDocument({
                url: 'offscreen.html',
                reasons: ['AUDIO_WORKLET'],
                justification: 'Audio processing for meeting transcription'
            });
            console.log('🎤 Offscreen audio processor ready');
        } catch (error) {
            console.log('Offscreen document already exists or not needed');
        }
    }

    setupMessageListeners() {
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // Keep the message channel open for async responses
        });

        // Listen for messages from content scripts
        chrome.runtime.onConnect.addListener((port) => {
            if (port.name === 'ai-mentor') {
                this.handlePortConnection(port);
            }
        });
    }

    setupTabListeners() {
        // Monitor tab updates to detect meeting platforms
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            if (changeInfo.status === 'complete' && tab.url) {
                this.checkMeetingPlatform(tabId, tab.url);
            }
        });

        // Monitor tab activation
        chrome.tabs.onActivated.addListener((activeInfo) => {
            this.updateActiveTab(activeInfo.tabId);
        });
    }

    setupAlarms() {
        // Create periodic alarms for background tasks
        chrome.alarms.create('healthCheck', { periodInMinutes: 5 });
        chrome.alarms.create('dataCleanup', { periodInMinutes: 30 });

        chrome.alarms.onAlarm.addListener((alarm) => {
            this.handleAlarm(alarm);
        });
    }

    async handleMessage(request, sender, sendResponse) {
        try {
            switch (request.action) {
                case 'aiRequest':
                    const aiResponse = await this.processAIRequest(request.data);
                    sendResponse({ success: true, data: aiResponse });
                    break;

                case 'askQuestion':
                    const questionResponse = await this.processAIQuestion(request.question);
                    sendResponse({ success: true, data: questionResponse });
                    break;

                case 'expertResponse':
                    const expertResponse = await this.processExpertQuestion(request.data);
                    sendResponse({ success: true, data: expertResponse });
                    break;

                case 'uploadResume':
                    const resumeResponse = await this.processResumeUpload(request.data);
                    sendResponse({ success: true, data: resumeResponse });
                    break;

                case 'saveTranscript':
                    await this.saveTranscript(request.data);
                    sendResponse({ success: true });
                    break;

                case 'getSettings':
                    const settings = await this.getSettings();
                    sendResponse({ success: true, data: settings });
                    break;

                case 'updateSettings':
                    await this.updateSettings(request.data);
                    sendResponse({ success: true });
                    break;

                case 'logActivity':
                    await this.logActivity(request.data);
                    sendResponse({ success: true });
                    break;

                case 'getMeetingStatus':
                    const status = await this.getMeetingStatus(sender.tab.id);
                    sendResponse({ success: true, data: status });
                    break;

                case 'startMeetingRecording':
                    await this.startMeetingRecording();
                    sendResponse({ success: true });
                    break;

                case 'stopMeetingRecording':
                    await this.stopMeetingRecording();
                    sendResponse({ success: true });
                    break;

                case 'newTranscription':
                    await this.processTranscription(request.data);
                    sendResponse({ success: true });
                    break;

                case 'recordingStarted':
                case 'recordingStopped':
                    console.log(`📹 ${request.action}:`, request.timestamp);
                    break;

                default:
                    sendResponse({ success: false, error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Background service error:', error);
            sendResponse({ success: false, error: error.message });
        }
    }

    handlePortConnection(port) {
        console.log('Content script connected via port');
        
        port.onMessage.addListener(async (msg) => {
            switch (msg.type) {
                case 'streamingRequest':
                    await this.handleStreamingAIRequest(msg.data, port);
                    break;
                
                case 'heartbeat':
                    port.postMessage({ type: 'heartbeatResponse', timestamp: Date.now() });
                    break;
            }
        });

        port.onDisconnect.addListener(() => {
            console.log('Content script disconnected');
        });
    }

    async processAIRequest(data) {
        const { question, context } = data;
        
        try {
            // Make request to local AI service
            const response = await fetch('http://localhost:8084/api/expert-ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    context: {
                        ...context,
                        timestamp: new Date().toISOString(),
                        source: 'browser_extension'
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`AI Service responded with status: ${response.status}`);
            }

            const aiResponse = await response.json();
            
            // Log the interaction
            await this.logActivity({
                type: 'ai_request',
                question: question,
                response: aiResponse.response,
                context: context,
                timestamp: new Date().toISOString()
            });

            return aiResponse;
        } catch (error) {
            console.error('AI request failed:', error);
            throw new Error('AI service is currently unavailable');
        }
    }

    async processAIQuestion(question) {
        try {
            // Make simple question request to local AI service
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    context: {
                        timestamp: new Date().toISOString(),
                        source: 'popup'
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`AI Service responded with status: ${response.status}`);
            }

            const aiResponse = await response.json();
            console.log('✅ AI question processed successfully');
            return aiResponse;
        } catch (error) {
            console.error('❌ AI question failed:', error);
            throw new Error('AI service is currently unavailable');
        }
    }

    async processExpertQuestion(data) {
        try {
            console.log('🧠 Processing expert engineering question...');
            
            const { question, context } = data;
            
            // Make expert question request to local AI service
            const response = await fetch('http://localhost:8084/api/expert-ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    context: {
                        ...context,
                        timestamp: new Date().toISOString(),
                        source: 'expert_assistant'
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Expert AI Service responded with status: ${response.status}`);
            }

            const aiResponse = await response.json();
            console.log('✅ Expert AI question processed successfully');
            return aiResponse;
        } catch (error) {
            console.error('❌ Expert AI question failed:', error);
            throw new Error('Expert AI service is currently unavailable');
        }
    }

    async processResumeUpload(data) {
        try {
            console.log('📄 Processing resume upload:', data.fileName);
            
            const { fileName, content, fileType } = data;
            
            // Send resume to AI service for processing and storage
            const response = await fetch('http://localhost:8084/api/resume-upload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fileName: fileName,
                    content: content,
                    fileType: fileType,
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error(`Resume upload service responded with status: ${response.status}`);
            }

            const result = await response.json();
            
            // Store resume data locally for quick access
            await chrome.storage.local.set({
                userResume: {
                    fileName: fileName,
                    uploadDate: new Date().toISOString(),
                    processed: true,
                    summary: result.summary || 'Resume processed successfully'
                }
            });

            console.log('✅ Resume processed and stored successfully');
            return result;
            
        } catch (error) {
            console.error('❌ Resume processing failed:', error);
            throw new Error('Resume processing service is currently unavailable');
        }
    }

    async handleStreamingAIRequest(data, port) {
        // Handle streaming AI responses for real-time interactions
        try {
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                port.postMessage({
                    type: 'streamingResponse',
                    chunk: chunk,
                    done: false
                });
            }

            port.postMessage({
                type: 'streamingResponse',
                done: true
            });
        } catch (error) {
            port.postMessage({
                type: 'streamingError',
                error: error.message
            });
        }
    }

    async checkMeetingPlatform(tabId, url) {
        const meetingPlatforms = [
            { name: 'zoom', pattern: /zoom\.us/ },
            { name: 'teams', pattern: /teams\.microsoft\.com/ },
            { name: 'meet', pattern: /meet\.google\.com/ },
            { name: 'webex', pattern: /webex\.com/ }
        ];

        const platform = meetingPlatforms.find(p => p.pattern.test(url));
        
        if (platform) {
            // Inject content script if meeting platform detected
            try {
                await chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    files: ['content.js']
                });
                
                console.log(`✅ Content script injected for ${platform.name}`);
            } catch (error) {
                console.error('Failed to inject content script:', error);
            }
        }
    }

    async updateActiveTab(tabId) {
        // Store the currently active tab for context
        await chrome.storage.local.set({ activeTabId: tabId });
    }

    async saveTranscript(data) {
        const { meetingId, transcript, timestamp } = data;
        
        // Save transcript to storage
        const key = `transcript_${meetingId}_${Date.now()}`;
        await chrome.storage.local.set({
            [key]: {
                transcript: transcript,
                timestamp: timestamp,
                meetingId: meetingId
            }
        });

        // Also send to AI service for analysis
        try {
            await fetch('http://localhost:8084/api/transcript', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } catch (error) {
            console.error('Failed to send transcript to AI service:', error);
        }
    }

    async getSettings() {
        const defaultSettings = {
            autoRespond: true,
            monitorChat: true,
            showOverlay: true,
            audioProcessing: false,
            language: 'english',
            responseDelay: 2000
        };

        const result = await chrome.storage.sync.get(defaultSettings);
        return result;
    }

    async updateSettings(settings) {
        await chrome.storage.sync.set(settings);
        
        // Notify all content scripts of settings change
        const tabs = await chrome.tabs.query({});
        tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, {
                action: 'settingsUpdated',
                settings: settings
            }).catch(() => {
                // Ignore errors for tabs without content scripts
            });
        });
    }

    async logActivity(data) {
        const logEntry = {
            ...data,
            id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            timestamp: data.timestamp || new Date().toISOString()
        };

        // Store locally
        const key = `activity_${Date.now()}`;
        await chrome.storage.local.set({ [key]: logEntry });

        // Send to AI service for analytics
        try {
            await fetch('http://localhost:8084/api/activity', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(logEntry)
            });
        } catch (error) {
            console.error('Failed to log activity:', error);
        }
    }

    async getMeetingStatus(tabId) {
        try {
            const response = await chrome.tabs.sendMessage(tabId, {
                action: 'getStatus'
            });
            return response;
        } catch (error) {
            return { monitoring: false, platform: null };
        }
    }

    async handleAlarm(alarm) {
        switch (alarm.name) {
            case 'healthCheck':
                await this.performHealthCheck();
                break;
            
            case 'dataCleanup':
                await this.cleanupOldData();
                break;
        }
    }

    async performHealthCheck() {
        console.log('🔍 Performing health check...');
        try {
            // Check if AI service is responsive
            const response = await fetch('http://localhost:8084/api/health', {
                method: 'GET',
                timeout: 5000
            });
            
            console.log('📡 Health check response:', response.status, response.ok);
            const isHealthy = response.ok;
            const healthData = {
                status: isHealthy ? 'healthy' : 'degraded',
                lastCheck: new Date().toISOString()
            };
            
            await chrome.storage.local.set({ serviceHealth: healthData });
            console.log('✅ Health check completed, stored data:', healthData);
        } catch (error) {
            console.error('❌ Health check failed:', error);
            const errorData = {
                status: 'unhealthy',
                lastCheck: new Date().toISOString(),
                error: error.message
            };
            await chrome.storage.local.set({ serviceHealth: errorData });
            console.log('💾 Error data stored:', errorData);
        }
    }

    async cleanupOldData() {
        // Clean up old transcripts and activity logs (older than 7 days)
        const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        const storage = await chrome.storage.local.get();
        
        const keysToRemove = Object.keys(storage).filter(key => {
            if (key.startsWith('transcript_') || key.startsWith('activity_')) {
                const timestamp = parseInt(key.split('_')[1]);
                return timestamp && timestamp < weekAgo;
            }
            return false;
        });

        if (keysToRemove.length > 0) {
            await chrome.storage.local.remove(keysToRemove);
            console.log(`🧹 Cleaned up ${keysToRemove.length} old data entries`);
        }
    }

    async startMeetingRecording() {
        try {
            console.log('🎬 Starting meeting recording...');
            
            // Send message to offscreen document to start recording
            await chrome.runtime.sendMessage({
                action: 'startRecording'
            });

            // Store recording state
            await chrome.storage.local.set({
                isRecording: true,
                recordingStarted: new Date().toISOString()
            });

            console.log('✅ Meeting recording started');
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            throw error;
        }
    }

    async stopMeetingRecording() {
        try {
            console.log('⏹️ Stopping meeting recording...');
            
            // Send message to offscreen document to stop recording
            await chrome.runtime.sendMessage({
                action: 'stopRecording'
            });

            // Update recording state
            await chrome.storage.local.set({
                isRecording: false,
                recordingStopped: new Date().toISOString()
            });

            console.log('✅ Meeting recording stopped');
        } catch (error) {
            console.error('❌ Failed to stop recording:', error);
            throw error;
        }
    }

    async processTranscription(transcriptionData) {
        try {
            console.log('📝 Processing transcription:', transcriptionData);
            
            // Store transcription in local storage
            const existing = await chrome.storage.local.get(['conversationHistory']);
            const history = existing.conversationHistory || [];
            history.push(transcriptionData);
            
            await chrome.storage.local.set({ conversationHistory: history });

            // Send to AI service for context enhancement
            const response = await fetch('http://localhost:8084/api/transcription', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transcription: transcriptionData,
                    context: 'meeting'
                })
            });

            if (response.ok) {
                console.log('✅ Transcription processed by AI');
            }
        } catch (error) {
            console.error('❌ Failed to process transcription:', error);
        }
    }
}

// Initialize background service
try {
    console.log('🎯 Initializing meeting detector...');
    const meetingDetector = new MeetingDetector();
    console.log('✅ Meeting detector ready');
    
    console.log('🔧 Initializing background service...');
    const backgroundService = new BackgroundService();
    console.log('✅ Background service ready');
    
    console.log('🚀 AI Mentor Assistant Background Script fully loaded!');
} catch (error) {
    console.error('❌ Failed to initialize background script:', error);
}
