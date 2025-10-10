/**
 * Advanced AI Brain Content Script
 * Enhanced browser extension with context awareness and real-time assistance
 * Inspired by Cluely's context processing and Firefly's meeting intelligence
 */

class AdvancedAIAssistant {
    constructor() {
        this.isActive = false;
        this.isStealthMode = true;
        this.recognition = null;
        this.overlay = null;
        this.contextProcessor = new ContextProcessor();
        this.meetingIntelligence = new MeetingIntelligence();
        this.taskManager = new TaskManager();
        this.codeAnalyzer = new CodeAnalyzer();
        
        // Real-time processing
        this.lastApiCall = 0;
        this.contextHistory = [];
        this.activeConnections = new Map();
        
        // User authentication
        this.userToken = null;
        this.userProfile = null;
        
        // Configuration
        this.config = {
            apiBaseUrl: 'https://your-domain.com/api',
            stealthMode: true,
            autoProcessing: true,
            contextWindow: 100,
            confidenceThreshold: 0.7
        };
        
        console.log('🧠 Advanced AI Assistant initialized');
    }

    async initialize() {
        console.log('🚀 Initializing Advanced AI Assistant...');
        
        // Load user configuration and authentication
        await this.loadUserConfig();
        
        // Initialize AI brain connection
        await this.initializeAIBrain();
        
        // Setup context detection
        this.setupContextDetection();
        
        // Initialize speech recognition
        this.initializeSpeechRecognition();
        
        // Create intelligent overlay
        this.createIntelligentOverlay();
        
        // Setup real-time processing
        this.setupRealTimeProcessing();
        
        // Setup hotkeys and shortcuts
        this.setupAdvancedHotkeys();
        
        // Initialize platform-specific features
        this.initializePlatformFeatures();
        
        console.log('✅ Advanced AI Assistant fully initialized');
    }

    async loadUserConfig() {
        try {
            const result = await chrome.storage.sync.get(['userToken', 'userProfile', 'aiConfig']);
            
            this.userToken = result.userToken;
            this.userProfile = result.userProfile;
            
            if (result.aiConfig) {
                this.config = { ...this.config, ...result.aiConfig };
            }
            
            console.log('📋 User configuration loaded');
        } catch (error) {
            console.error('❌ Failed to load user config:', error);
        }
    }

    async initializeAIBrain() {
        try {
            // Connect to AI Brain backend
            const response = await fetch(`${this.config.apiBaseUrl}/brain/initialize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    platform: this.detectPlatform(),
                    context: this.getCurrentContext(),
                    capabilities: this.getClientCapabilities()
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                console.log('🧠 AI Brain connected:', this.sessionId);
            }
        } catch (error) {
            console.error('❌ AI Brain initialization failed:', error);
        }
    }

    setupContextDetection() {
        // Enhanced context detection for different platforms
        const platform = this.detectPlatform();
        
        switch (platform) {
            case 'google-meet':
                this.setupGoogleMeetContext();
                break;
            case 'zoom':
                this.setupZoomContext();
                break;
            case 'teams':
                this.setupTeamsContext();
                break;
            case 'jira':
                this.setupJiraContext();
                break;
            case 'github':
                this.setupGitHubContext();
                break;
            case 'linear':
                this.setupLinearContext();
                break;
            default:
                this.setupGenericContext();
        }
    }

    static isHostOrSubdomain(host, domain) {
        return host === domain || host.endsWith('.' + domain);
    }

    detectPlatform() {
        const hostname = window.location.hostname;
        const pathname = window.location.pathname;
        
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'meet.google.com')) return 'google-meet';
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'zoom.us')) return 'zoom';
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'teams.microsoft.com')) return 'teams';
        if (
            AdvancedAIAssistant.isHostOrSubdomain(hostname, 'atlassian.net') ||
            hostname.includes('jira') // Can't fix generically; optionally could improve.
        ) return 'jira';
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'github.com')) return 'github';
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'linear.app')) return 'linear';
        if (AdvancedAIAssistant.isHostOrSubdomain(hostname, 'slack.com')) return 'slack';
        
        return 'generic';
    }

    setupGoogleMeetContext() {
        console.log('🔧 Setting up Google Meet context detection');
        
        // Enhanced meeting detection
        this.observeElement('[data-meeting-title]', (element) => {
            const meetingTitle = element.textContent;
            this.processMeetingContext({ title: meetingTitle, platform: 'google-meet' });
        });
        
        // Participant detection
        this.observeElement('[data-participant-id]', (element) => {
            const participants = this.extractParticipants();
            this.processMeetingContext({ participants, platform: 'google-meet' });
        });
        
        // Screen sharing detection
        this.observeElement('[data-screen-share-active]', () => {
            this.processMeetingContext({ screenSharing: true, platform: 'google-meet' });
        });
        
        // Chat monitoring
        this.observeElement('[data-message-text]', (element) => {
            const message = element.textContent;
            this.processChatMessage(message);
        });
    }

    setupJiraContext() {
        console.log('🔧 Setting up JIRA context detection');
        
        // Issue detection
        this.observeElement('[data-testid="issue.views.issue-base.foundation.summary.heading"]', (element) => {
            const issueTitle = element.textContent;
            const issueKey = this.extractIssueKey();
            this.processTaskContext({ 
                title: issueTitle, 
                key: issueKey, 
                platform: 'jira',
                type: 'issue_view'
            });
        });
        
        // Sprint planning detection
        this.observeElement('[data-testid="software-backlog"]', () => {
            this.processTaskContext({ 
                platform: 'jira',
                type: 'sprint_planning',
                context: 'backlog'
            });
        });
        
        // Comment detection
        this.observeElement('[data-testid="issue.activity.comment"]', (element) => {
            const comment = element.textContent;
            this.processTaskContext({
                platform: 'jira',
                type: 'comment',
                content: comment
            });
        });
    }

    setupGitHubContext() {
        console.log('🔧 Setting up GitHub context detection');
        
        // Repository detection
        const repoName = this.extractRepoName();
        if (repoName) {
            this.processCodeContext({
                repository: repoName,
                platform: 'github',
                type: 'repository'
            });
        }
        
        // Pull request detection
        this.observeElement('.js-issue-title', (element) => {
            const prTitle = element.textContent;
            const prNumber = this.extractPRNumber();
            this.processCodeContext({
                title: prTitle,
                number: prNumber,
                platform: 'github',
                type: 'pull_request'
            });
        });
        
        // Code review detection
        this.observeElement('.review-comment-contents', (element) => {
            const comment = element.textContent;
            this.processCodeContext({
                platform: 'github',
                type: 'code_review',
                comment: comment
            });
        });
        
        // File editing detection
        this.observeElement('.file-editor-textarea', (element) => {
            const code = element.value;
            const fileName = this.extractFileName();
            this.processCodeContext({
                fileName: fileName,
                code: code,
                platform: 'github',
                type: 'code_editing'
            });
        });
    }

    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                if (finalTranscript) {
                    this.processSpeechInput(finalTranscript);
                }
                
                this.updateOverlayTranscript(interimTranscript, finalTranscript);
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
            };
            
            // Auto-start in stealth mode
            if (this.config.autoProcessing) {
                this.startListening();
            }
        }
    }

    createIntelligentOverlay() {
        // Create advanced overlay with multiple panels
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        this.overlay.className = 'ai-overlay-container';
        
        this.overlay.innerHTML = `
            <div class="ai-overlay-header">
                <div class="ai-status-indicator"></div>
                <div class="ai-platform-info">${this.detectPlatform()}</div>
                <div class="ai-controls">
                    <button class="ai-btn" id="ai-toggle-stealth">👁️</button>
                    <button class="ai-btn" id="ai-toggle-listen">🎤</button>
                    <button class="ai-btn" id="ai-minimize">➖</button>
                </div>
            </div>
            
            <div class="ai-overlay-content">
                <div class="ai-panel ai-context-panel">
                    <div class="ai-panel-header">Context</div>
                    <div class="ai-context-display"></div>
                </div>
                
                <div class="ai-panel ai-insights-panel">
                    <div class="ai-panel-header">AI Insights</div>
                    <div class="ai-insights-display"></div>
                </div>
                
                <div class="ai-panel ai-actions-panel">
                    <div class="ai-panel-header">Suggested Actions</div>
                    <div class="ai-actions-display"></div>
                </div>
                
                <div class="ai-panel ai-transcript-panel">
                    <div class="ai-panel-header">Live Transcript</div>
                    <div class="ai-transcript-display"></div>
                </div>
            </div>
            
            <div class="ai-overlay-footer">
                <div class="ai-confidence-meter">
                    <div class="ai-confidence-bar"></div>
                    <span class="ai-confidence-text">0%</span>
                </div>
                <div class="ai-quick-actions">
                    <button class="ai-quick-btn" data-action="summarize">📋</button>
                    <button class="ai-quick-btn" data-action="create-task">📝</button>
                    <button class="ai-quick-btn" data-action="generate-code">💻</button>
                    <button class="ai-quick-btn" data-action="analyze">🔍</button>
                </div>
            </div>
        `;
        
        // Add advanced styling
        this.addOverlayStyles();
        
        // Setup event listeners
        this.setupOverlayEvents();
        
        // Initially hidden for stealth
        if (this.config.stealthMode) {
            this.overlay.style.display = 'none';
        }
        
        document.body.appendChild(this.overlay);
    }

    addOverlayStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .ai-overlay-container {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 400px;
                max-height: 80vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
                backdrop-filter: blur(10px);
                color: white;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                z-index: 10000;
                overflow: hidden;
                transition: all 0.3s ease;
            }
            
            .ai-overlay-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 15px;
                background: rgba(255,255,255,0.1);
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }
            
            .ai-status-indicator {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #4CAF50;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
            
            .ai-platform-info {
                font-size: 12px;
                opacity: 0.8;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .ai-controls {
                display: flex;
                gap: 5px;
            }
            
            .ai-btn {
                background: rgba(255,255,255,0.2);
                border: none;
                border-radius: 8px;
                padding: 8px;
                color: white;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .ai-btn:hover {
                background: rgba(255,255,255,0.3);
                transform: scale(1.1);
            }
            
            .ai-overlay-content {
                max-height: 400px;
                overflow-y: auto;
                padding: 15px;
            }
            
            .ai-panel {
                margin-bottom: 15px;
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                overflow: hidden;
            }
            
            .ai-panel-header {
                padding: 10px 15px;
                background: rgba(255,255,255,0.2);
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .ai-context-display,
            .ai-insights-display,
            .ai-actions-display,
            .ai-transcript-display {
                padding: 15px;
                font-size: 14px;
                line-height: 1.4;
                min-height: 50px;
            }
            
            .ai-overlay-footer {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 15px;
                background: rgba(0,0,0,0.2);
                border-top: 1px solid rgba(255,255,255,0.2);
            }
            
            .ai-confidence-meter {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .ai-confidence-bar {
                width: 80px;
                height: 6px;
                background: rgba(255,255,255,0.3);
                border-radius: 3px;
                overflow: hidden;
            }
            
            .ai-confidence-bar::before {
                content: '';
                display: block;
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #8BC34A);
                width: var(--confidence, 0%);
                transition: width 0.3s ease;
            }
            
            .ai-confidence-text {
                font-size: 12px;
                font-weight: 600;
            }
            
            .ai-quick-actions {
                display: flex;
                gap: 5px;
            }
            
            .ai-quick-btn {
                background: rgba(255,255,255,0.2);
                border: none;
                border-radius: 50%;
                width: 35px;
                height: 35px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 14px;
            }
            
            .ai-quick-btn:hover {
                background: rgba(255,255,255,0.3);
                transform: scale(1.1);
            }
            
            /* Stealth mode */
            .ai-overlay-stealth {
                opacity: 0.1;
                transform: scale(0.5);
                pointer-events: none;
            }
            
            /* Mobile responsive */
            @media (max-width: 768px) {
                .ai-overlay-container {
                    width: calc(100vw - 40px);
                    right: 20px;
                }
            }
        `;
        
        document.head.appendChild(style);
    }

    setupOverlayEvents() {
        // Toggle stealth mode
        this.overlay.querySelector('#ai-toggle-stealth').addEventListener('click', () => {
            this.toggleStealthMode();
        });
        
        // Toggle listening
        this.overlay.querySelector('#ai-toggle-listen').addEventListener('click', () => {
            this.toggleListening();
        });
        
        // Minimize overlay
        this.overlay.querySelector('#ai-minimize').addEventListener('click', () => {
            this.minimizeOverlay();
        });
        
        // Quick actions
        this.overlay.querySelectorAll('.ai-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.executeQuickAction(action);
            });
        });
    }

    setupRealTimeProcessing() {
        // Real-time context monitoring
        setInterval(() => {
            this.processCurrentContext();
        }, 5000); // Every 5 seconds
        
        // Intelligent response timing
        setInterval(() => {
            this.processIntelligentResponses();
        }, 2000); // Every 2 seconds
        
        // Memory optimization
        setInterval(() => {
            this.optimizeMemory();
        }, 60000); // Every minute
    }

    setupAdvancedHotkeys() {
        document.addEventListener('keydown', (event) => {
            // Ctrl+Alt+A: Toggle AI Assistant
            if (event.ctrlKey && event.altKey && event.key === 'a') {
                event.preventDefault();
                this.toggleAssistant();
            }
            
            // Ctrl+Alt+S: Toggle Stealth Mode
            if (event.ctrlKey && event.altKey && event.key === 's') {
                event.preventDefault();
                this.toggleStealthMode();
            }
            
            // Ctrl+Alt+L: Toggle Listening
            if (event.ctrlKey && event.altKey && event.key === 'l') {
                event.preventDefault();
                this.toggleListening();
            }
            
            // Ctrl+Alt+T: Create Task
            if (event.ctrlKey && event.altKey && event.key === 't') {
                event.preventDefault();
                this.executeQuickAction('create-task');
            }
            
            // Ctrl+Alt+C: Generate Code
            if (event.ctrlKey && event.altKey && event.key === 'c') {
                event.preventDefault();
                this.executeQuickAction('generate-code');
            }
        });
    }

    initializePlatformFeatures() {
        const platform = this.detectPlatform();
        
        switch (platform) {
            case 'google-meet':
                this.initializeGoogleMeetFeatures();
                break;
            case 'jira':
                this.initializeJiraFeatures();
                break;
            case 'github':
                this.initializeGitHubFeatures();
                break;
            case 'linear':
                this.initializeLinearFeatures();
                break;
        }
    }

    initializeGoogleMeetFeatures() {
        // Enhanced meeting intelligence
        console.log('🎥 Initializing Google Meet features');
        
        // Auto-detect meeting start
        this.observeElement('[data-meeting-state="active"]', () => {
            this.startMeetingAssistance();
        });
        
        // Auto-detect screen sharing
        this.observeElement('[data-screen-share="true"]', () => {
            this.processMeetingContext({ event: 'screen_share_started' });
        });
        
        // Monitor participant changes
        this.observeElement('[data-participant-count]', (element) => {
            const count = parseInt(element.dataset.participantCount);
            this.processMeetingContext({ event: 'participant_change', count: count });
        });
    }

    initializeJiraFeatures() {
        console.log('📋 Initializing JIRA features');
        
        // Auto-detect issue creation
        this.observeElement('[data-testid="issue.create.title"]', () => {
            this.showTaskCreationAssistance();
        });
        
        // Sprint planning assistance
        this.observeElement('[data-testid="software-backlog.sprint-header"]', () => {
            this.showSprintPlanningAssistance();
        });
    }

    initializeGitHubFeatures() {
        console.log('💻 Initializing GitHub features');
        
        // Auto-detect PR creation
        this.observeElement('[data-testid="pull-request-form"]', () => {
            this.showPRCreationAssistance();
        });
        
        // Code review assistance
        this.observeElement('.review-comment-form', () => {
            this.showCodeReviewAssistance();
        });
    }

    // Context Processing Methods
    async processMeetingContext(context) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/brain/process-context`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    context_type: 'meeting',
                    data: context,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateOverlayWithMeetingInsights(result);
            }
        } catch (error) {
            console.error('❌ Failed to process meeting context:', error);
        }
    }

    async processTaskContext(context) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/brain/process-context`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    context_type: 'task',
                    data: context,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateOverlayWithTaskInsights(result);
            }
        } catch (error) {
            console.error('❌ Failed to process task context:', error);
        }
    }

    async processCodeContext(context) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/brain/process-context`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    context_type: 'code',
                    data: context,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateOverlayWithCodeInsights(result);
            }
        } catch (error) {
            console.error('❌ Failed to process code context:', error);
        }
    }

    async processSpeechInput(transcript) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/brain/process-speech`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    transcript: transcript,
                    platform: this.detectPlatform(),
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateOverlayWithSpeechInsights(result);
            }
        } catch (error) {
            console.error('❌ Failed to process speech:', error);
        }
    }

    // Overlay Update Methods
    updateOverlayWithMeetingInsights(insights) {
        const contextDisplay = this.overlay.querySelector('.ai-context-display');
        const insightsDisplay = this.overlay.querySelector('.ai-insights-display');
        const actionsDisplay = this.overlay.querySelector('.ai-actions-display');
        
        if (insights.context) {
            contextDisplay.innerHTML = `
                <div class="context-item">
                    <strong>Meeting:</strong> ${insights.context.title || 'Unnamed Meeting'}
                </div>
                <div class="context-item">
                    <strong>Participants:</strong> ${insights.context.participant_count || 'Unknown'}
                </div>
                <div class="context-item">
                    <strong>Duration:</strong> ${insights.context.duration || 'Ongoing'}
                </div>
            `;
        }
        
        if (insights.insights) {
            insightsDisplay.innerHTML = insights.insights.map(insight => 
                `<div class="insight-item">💡 ${insight}</div>`
            ).join('');
        }
        
        if (insights.suggested_actions) {
            actionsDisplay.innerHTML = insights.suggested_actions.map(action => 
                `<div class="action-item" data-action="${action.type}">
                    <span class="action-icon">${action.icon || '⚡'}</span>
                    <span class="action-text">${action.description}</span>
                </div>`
            ).join('');
        }
        
        this.updateConfidenceMeter(insights.confidence || 0);
    }

    updateOverlayWithTaskInsights(insights) {
        const contextDisplay = this.overlay.querySelector('.ai-context-display');
        const insightsDisplay = this.overlay.querySelector('.ai-insights-display');
        
        if (insights.context) {
            contextDisplay.innerHTML = `
                <div class="context-item">
                    <strong>Task:</strong> ${insights.context.title || 'Current Task'}
                </div>
                <div class="context-item">
                    <strong>Type:</strong> ${insights.context.type || 'Unknown'}
                </div>
                <div class="context-item">
                    <strong>Priority:</strong> ${insights.context.priority || 'Medium'}
                </div>
            `;
        }
        
        if (insights.insights) {
            insightsDisplay.innerHTML = insights.insights.map(insight => 
                `<div class="insight-item">📋 ${insight}</div>`
            ).join('');
        }
        
        this.updateConfidenceMeter(insights.confidence || 0);
    }

    updateOverlayWithCodeInsights(insights) {
        const contextDisplay = this.overlay.querySelector('.ai-context-display');
        const insightsDisplay = this.overlay.querySelector('.ai-insights-display');
        
        if (insights.context) {
            contextDisplay.innerHTML = `
                <div class="context-item">
                    <strong>Repository:</strong> ${insights.context.repository || 'Unknown'}
                </div>
                <div class="context-item">
                    <strong>File:</strong> ${insights.context.file || 'Multiple files'}
                </div>
                <div class="context-item">
                    <strong>Language:</strong> ${insights.context.language || 'Unknown'}
                </div>
            `;
        }
        
        if (insights.insights) {
            insightsDisplay.innerHTML = insights.insights.map(insight => 
                `<div class="insight-item">💻 ${insight}</div>`
            ).join('');
        }
        
        this.updateConfidenceMeter(insights.confidence || 0);
    }

    updateConfidenceMeter(confidence) {
        const confidenceBar = this.overlay.querySelector('.ai-confidence-bar');
        const confidenceText = this.overlay.querySelector('.ai-confidence-text');
        
        confidenceBar.style.setProperty('--confidence', `${confidence * 100}%`);
        confidenceText.textContent = `${Math.round(confidence * 100)}%`;
    }

    // Quick Actions
    async executeQuickAction(action) {
        console.log(`🚀 Executing quick action: ${action}`);
        
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/brain/quick-action`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.userToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    action: action,
                    context: this.getCurrentContext(),
                    timestamp: new Date().toISOString()
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.handleQuickActionResult(action, result);
            }
        } catch (error) {
            console.error(`❌ Quick action ${action} failed:`, error);
        }
    }

    handleQuickActionResult(action, result) {
        switch (action) {
            case 'summarize':
                this.showSummaryModal(result.summary);
                break;
            case 'create-task':
                this.showTaskCreationModal(result.task_suggestion);
                break;
            case 'generate-code':
                this.showCodeGenerationModal(result.code_suggestion);
                break;
            case 'analyze':
                this.showAnalysisModal(result.analysis);
                break;
        }
    }

    // Control Methods
    toggleStealthMode() {
        this.config.stealthMode = !this.config.stealthMode;
        
        if (this.config.stealthMode) {
            this.overlay.classList.add('ai-overlay-stealth');
        } else {
            this.overlay.classList.remove('ai-overlay-stealth');
        }
        
        console.log(`👁️ Stealth mode: ${this.config.stealthMode ? 'ON' : 'OFF'}`);
    }

    toggleListening() {
        if (this.recognition) {
            if (this.isListening) {
                this.recognition.stop();
                this.isListening = false;
            } else {
                this.recognition.start();
                this.isListening = true;
            }
            
            console.log(`🎤 Listening: ${this.isListening ? 'ON' : 'OFF'}`);
        }
    }

    startListening() {
        if (this.recognition && !this.isListening) {
            this.recognition.start();
            this.isListening = true;
        }
    }

    minimizeOverlay() {
        this.overlay.style.transform = 'scale(0.1)';
        this.overlay.style.opacity = '0.3';
        
        setTimeout(() => {
            this.overlay.style.transform = 'scale(1)';
            this.overlay.style.opacity = '1';
        }, 3000);
    }

    // Utility Methods
    observeElement(selector, callback) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        const element = node.matches && node.matches(selector) ? 
                            node : node.querySelector && node.querySelector(selector);
                        if (element) {
                            callback(element);
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Check existing elements
        const existingElement = document.querySelector(selector);
        if (existingElement) {
            callback(existingElement);
        }
    }

    getCurrentContext() {
        return {
            url: window.location.href,
            platform: this.detectPlatform(),
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };
    }

    getClientCapabilities() {
        return {
            speechRecognition: 'webkitSpeechRecognition' in window,
            webRTC: 'RTCPeerConnection' in window,
            notifications: 'Notification' in window,
            storage: 'localStorage' in window,
            clipboard: 'clipboard' in navigator,
            geolocation: 'geolocation' in navigator
        };
    }

    // Extract utility methods
    extractParticipants() {
        // Implementation depends on platform
        return [];
    }

    extractIssueKey() {
        const match = window.location.pathname.match(/\/([A-Z]+-\d+)/);
        return match ? match[1] : null;
    }

    extractRepoName() {
        const match = window.location.pathname.match(/\/([^\/]+\/[^\/]+)/);
        return match ? match[1] : null;
    }

    extractPRNumber() {
        const match = window.location.pathname.match(/\/pull\/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    extractFileName() {
        const match = window.location.pathname.match(/\/([^\/]+\.[^\/]+)$/);
        return match ? match[1] : null;
    }
}

// Helper Classes
class ContextProcessor {
    constructor() {
        this.contextBuffer = [];
        this.maxBufferSize = 100;
    }
    
    addContext(context) {
        this.contextBuffer.push({
            ...context,
            timestamp: new Date().toISOString()
        });
        
        if (this.contextBuffer.length > this.maxBufferSize) {
            this.contextBuffer.shift();
        }
    }
    
    getRecentContext(limit = 10) {
        return this.contextBuffer.slice(-limit);
    }
}

class MeetingIntelligence {
    constructor() {
        this.activeMeeting = null;
        this.participants = [];
        this.transcript = [];
    }
    
    startMeeting(context) {
        this.activeMeeting = {
            ...context,
            startTime: new Date().toISOString()
        };
    }
    
    endMeeting() {
        if (this.activeMeeting) {
            this.activeMeeting.endTime = new Date().toISOString();
            return this.activeMeeting;
        }
        return null;
    }
}

class TaskManager {
    constructor() {
        this.activeTasks = [];
        this.taskHistory = [];
    }
    
    addTask(task) {
        this.activeTasks.push({
            ...task,
            createdAt: new Date().toISOString()
        });
    }
    
    completeTask(taskId) {
        const taskIndex = this.activeTasks.findIndex(t => t.id === taskId);
        if (taskIndex >= 0) {
            const task = this.activeTasks.splice(taskIndex, 1)[0];
            task.completedAt = new Date().toISOString();
            this.taskHistory.push(task);
            return task;
        }
        return null;
    }
}

class CodeAnalyzer {
    constructor() {
        this.analysisCache = new Map();
    }
    
    async analyzeCode(code, language) {
        const cacheKey = this.generateCacheKey(code, language);
        
        if (this.analysisCache.has(cacheKey)) {
            return this.analysisCache.get(cacheKey);
        }
        
        // Simple analysis - in production, use more sophisticated analysis
        const analysis = {
            language: language,
            lines: code.split('\n').length,
            complexity: this.calculateComplexity(code),
            issues: this.findIssues(code),
            suggestions: this.generateSuggestions(code)
        };
        
        this.analysisCache.set(cacheKey, analysis);
        return analysis;
    }
    
    calculateComplexity(code) {
        // Simple complexity calculation
        const patterns = ['if ', 'for ', 'while ', 'switch ', 'catch '];
        return patterns.reduce((count, pattern) => {
            return count + (code.match(new RegExp(pattern, 'g')) || []).length;
        }, 1);
    }
    
    findIssues(code) {
        const issues = [];
        
        // Check for console.log statements
        if (code.includes('console.log')) {
            issues.push('Found console.log statements');
        }
        
        // Check for TODO comments
        if (code.includes('TODO')) {
            issues.push('Found TODO comments');
        }
        
        return issues;
    }
    
    generateSuggestions(code) {
        const suggestions = [];
        
        if (code.length > 1000) {
            suggestions.push('Consider breaking this code into smaller functions');
        }
        
        if (!code.includes('//') && !code.includes('/*')) {
            suggestions.push('Consider adding comments to improve readability');
        }
        
        return suggestions;
    }
    
    generateCacheKey(code, language) {
        return `${language}_${code.length}_${this.hashCode(code)}`;
    }
    
    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash;
    }
}

// Initialize the assistant when the page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const assistant = new AdvancedAIAssistant();
        assistant.initialize();
    });
} else {
    const assistant = new AdvancedAIAssistant();
    assistant.initialize();
}
