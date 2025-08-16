// Inter-Extension Communication Bridge
// Connects Browser Extension ↔ AI Service ↔ VS Code Extension

class ExtensionBridge {
    constructor() {
        this.serviceUrl = 'http://localhost:8080';
        this.sessionId = this.generateSessionId();
        this.meetingContext = null;
        this.codingContext = null;
        this.isInMeeting = false;
        this.isPairProgramming = false;
        this.init();
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    async init() {
        console.log('🔗 Extension Bridge initialized');
        this.startContextSyncing();
        this.setupMessageHandlers();
        this.monitorScreenCapture();
    }

    // ===========================================
    // MEETING CONTEXT MANAGEMENT
    // ===========================================

    async updateMeetingContext(context) {
        this.meetingContext = {
            ...context,
            timestamp: new Date().toISOString(),
            sessionId: this.sessionId
        };

        // Send to AI service for VS Code extension to access
        await this.syncContextToService();
        
        // Check if this is a coding/technical meeting
        if (this.isCodingMeeting(context)) {
            await this.notifyVSCodeExtension('meeting_started', this.meetingContext);
        }
    }

    isCodingMeeting(context) {
        const codingKeywords = [
            'code review', 'pair programming', 'development', 'implementation',
            'debugging', 'architecture', 'technical discussion', 'sprint',
            'standup', 'retrospective', 'planning', 'feature', 'bug fix'
        ];

        const meetingTitle = context.meetingTitle?.toLowerCase() || '';
        const participants = context.participants?.join(' ').toLowerCase() || '';
        const chatHistory = context.recentChat?.join(' ').toLowerCase() || '';

        const searchText = `${meetingTitle} ${participants} ${chatHistory}`;
        
        return codingKeywords.some(keyword => searchText.includes(keyword));
    }

    async detectScreenSharing() {
        // Detect when screen sharing starts (usually indicates coding session)
        this.isPairProgramming = true;
        
        const context = {
            type: 'screen_sharing_started',
            isPairProgramming: true,
            meetingContext: this.meetingContext,
            timestamp: new Date().toISOString()
        };

        await this.notifyVSCodeExtension('pair_programming_started', context);
    }

    monitorScreenCapture() {
        // Detect Chrome tabCapture/desktopCapture usage and notify backend when
        // the entire screen is selected. Chrome exposes capture details via
        // `chromeMediaSource` and `displaySurface` track settings.
        const backendUrl = 'http://localhost:8081/api/relay/mobile';

        const signalFullScreen = () => {
            fetch(backendUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'fullscreen_share',
                    fullscreen: true,
                    sessionId: this.sessionId
                })
            }).catch(() => {});
        };

        const checkStream = (stream) => {
            try {
                const [track] = stream.getVideoTracks();
                const settings = track?.getSettings ? track.getSettings() : {};
                const source = settings.chromeMediaSource;
                const surface = settings.displaySurface;
                // Chrome reports full-screen shares as chromeMediaSource "desktop"
                // with displaySurface "monitor".
                if ((source === 'desktop' || surface === 'monitor') && surface === 'monitor') {
                    signalFullScreen();
                }
            } catch (e) {
                // Ignore errors from unavailable settings
            }
        };

        if (navigator.mediaDevices) {
            if (navigator.mediaDevices.getDisplayMedia) {
                const origGetDisplayMedia = navigator.mediaDevices.getDisplayMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getDisplayMedia = async (constraints) => {
                    const stream = await origGetDisplayMedia(constraints);
                    checkStream(stream);
                    return stream;
                };
            }

            if (navigator.mediaDevices.getUserMedia) {
                const origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getUserMedia = async (constraints) => {
                    const stream = await origGetUserMedia(constraints);
                    checkStream(stream);
                    return stream;
                };
            }
        }

        if (chrome?.tabCapture?.capture) {
            const origTabCapture = chrome.tabCapture.capture.bind(chrome.tabCapture);
            chrome.tabCapture.capture = (options, callback) => {
                origTabCapture(options, (stream) => {
                    if (stream) {
                        checkStream(stream);
                    }
                    if (callback) callback(stream);
                });
            };
        }
    }

    // ===========================================
    // JIRA INTEGRATION BRIDGE
    // ===========================================

    async syncJiraContextFromMeeting(jiraTickets) {
        // When Jira tickets are discussed in meeting, sync to VS Code
        const jiraContext = {
            tickets: jiraTickets,
            discussedInMeeting: true,
            meetingContext: this.meetingContext,
            priority: 'high', // Meeting-discussed tickets are high priority
            timestamp: new Date().toISOString()
        };

        await this.syncToService('jira_context', jiraContext);
        await this.notifyVSCodeExtension('jira_tickets_discussed', jiraContext);
    }

    async extractJiraTicketsFromChat(chatMessage) {
        // Extract Jira ticket references from meeting chat
        const jiraPattern = /[A-Z]+-\d+/g;
        const tickets = chatMessage.match(jiraPattern) || [];
        
        if (tickets.length > 0) {
            await this.syncJiraContextFromMeeting(tickets);
        }
    }

    // ===========================================
    // CODING ASSISTANCE BRIDGE
    // ===========================================

    async handleCodingRequest(request) {
        // When someone in meeting asks for code implementation
        const codingContext = {
            request: request,
            meetingContext: this.meetingContext,
            isPairProgramming: this.isPairProgramming,
            priority: 'immediate',
            timestamp: new Date().toISOString()
        };

        // Send to VS Code extension for immediate assistance
        await this.notifyVSCodeExtension('coding_request', codingContext);
        
        // Also store in AI service for context
        await this.syncToService('coding_request', codingContext);
    }

    async listenForCodingRequests(message) {
        const codingTriggers = [
            'can you implement', 'let\'s code', 'write the code',
            'show me the implementation', 'how do we code this',
            'let\'s build', 'create a function', 'add this feature',
            'fix this bug', 'refactor this', 'optimize this'
        ];

        const messageText = message.toLowerCase();
        const isCodingRequest = codingTriggers.some(trigger => 
            messageText.includes(trigger)
        );

        if (isCodingRequest) {
            await this.handleCodingRequest(message);
        }
    }

    // ===========================================
    // VS CODE EXTENSION COMMUNICATION
    // ===========================================

    async notifyVSCodeExtension(action, data) {
        try {
            // Send via AI service as message queue
            await fetch(`${this.serviceUrl}/api/vscode-message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action,
                    data: data,
                    sessionId: this.sessionId,
                    timestamp: new Date().toISOString()
                })
            });
            
            console.log(`📤 Sent to VS Code: ${action}`);
        } catch (error) {
            console.error('Failed to notify VS Code extension:', error);
        }
    }

    async receivedFromVSCode(message) {
        // Handle messages from VS Code extension
        switch (message.action) {
            case 'code_generated':
                await this.handleCodeGenerated(message.data);
                break;
            
            case 'file_opened':
                await this.handleFileOpened(message.data);
                break;
                
            case 'task_started':
                await this.handleTaskStarted(message.data);
                break;
                
            case 'need_clarification':
                await this.requestMeetingClarification(message.data);
                break;
        }
    }

    // ===========================================
    // CONTEXT SYNCHRONIZATION
    // ===========================================

    async syncContextToService() {
        const fullContext = {
            sessionId: this.sessionId,
            meetingContext: this.meetingContext,
            codingContext: this.codingContext,
            isInMeeting: this.isInMeeting,
            isPairProgramming: this.isPairProgramming,
            timestamp: new Date().toISOString()
        };

        try {
            await fetch(`${this.serviceUrl}/api/sync-context`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fullContext)
            });
        } catch (error) {
            console.error('Failed to sync context:', error);
        }
    }

    async syncToService(type, data) {
        try {
            await fetch(`${this.serviceUrl}/api/bridge-sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: type,
                    data: data,
                    sessionId: this.sessionId,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.error(`Failed to sync ${type}:`, error);
        }
    }

    startContextSyncing() {
        // Sync context every 10 seconds
        setInterval(() => {
            this.syncContextToService();
        }, 10000);
    }

    // ===========================================
    // MEETING EVENT HANDLERS
    // ===========================================

    async handleCodeGenerated(codeData) {
        // When VS Code generates code, show in meeting overlay
        if (this.isInMeeting) {
            const notification = {
                type: 'code_generated',
                message: `✅ Code generated for: ${codeData.description}`,
                code: codeData.code,
                file: codeData.file
            };
            
            this.showMeetingNotification(notification);
        }
    }

    async handleFileOpened(fileData) {
        // When VS Code opens a file, update meeting context
        this.codingContext = {
            currentFile: fileData.path,
            language: fileData.language,
            relatedTickets: fileData.jiraTickets || [],
            timestamp: new Date().toISOString()
        };
        
        await this.syncContextToService();
    }

    async handleTaskStarted(taskData) {
        // When VS Code starts working on a task
        if (this.isInMeeting) {
            this.showMeetingNotification({
                type: 'task_started',
                message: `🎯 Started working on: ${taskData.summary}`,
                task: taskData
            });
        }
    }

    async requestMeetingClarification(question) {
        // When VS Code needs clarification, ask in meeting
        if (this.isInMeeting) {
            this.showMeetingNotification({
                type: 'clarification_needed',
                message: `❓ Need clarification: ${question}`,
                action: 'ask_in_meeting'
            });
        }
    }

    showMeetingNotification(notification) {
        // Show notification in meeting overlay
        const event = new CustomEvent('aiMentorNotification', {
            detail: notification
        });
        window.dispatchEvent(event);
    }

    // ===========================================
    // MESSAGE HANDLERS
    // ===========================================

    setupMessageHandlers() {
        // Listen for messages from browser extension
        window.addEventListener('message', (event) => {
            if (event.data.source === 'ai-mentor-browser') {
                this.handleBrowserMessage(event.data);
            }
        });

        // Listen for custom events
        window.addEventListener('aiMentorCodingRequest', (event) => {
            this.handleCodingRequest(event.detail.message);
        });

        window.addEventListener('aiMentorJiraDiscussion', (event) => {
            this.extractJiraTicketsFromChat(event.detail.message);
        });

        window.addEventListener('aiMentorScreenShare', () => {
            this.detectScreenSharing();
        });
    }

    async handleBrowserMessage(message) {
        switch (message.type) {
            case 'meeting_joined':
                this.isInMeeting = true;
                await this.updateMeetingContext(message.data);
                break;
                
            case 'meeting_ended':
                this.isInMeeting = false;
                this.isPairProgramming = false;
                await this.syncContextToService();
                break;
                
            case 'chat_message':
                await this.listenForCodingRequests(message.data.text);
                await this.extractJiraTicketsFromChat(message.data.text);
                break;
                
            case 'screen_share_started':
                await this.detectScreenSharing();
                break;
        }
    }
}

// Global bridge instance
window.extensionBridge = new ExtensionBridge();
