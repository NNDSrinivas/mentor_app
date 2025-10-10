// Advanced AI SDLC Assistant Background Service Worker
class AdvancedBackgroundService {
    constructor() {
        this.aiBackendUrl = 'http://localhost:8000';
        this.isConnected = false;
        this.activeFeatures = new Set();
        this.sessionData = {
            startTime: Date.now(),
            interactions: 0,
            contextSwitches: 0,
            aiResponses: 0
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeStorage();
        this.connectToAIBackend();
        this.startPeriodicTasks();
    }

    setupEventListeners() {
        // Extension lifecycle
        chrome.runtime.onInstalled.addListener((details) => {
            this.handleInstall(details);
        });

        chrome.runtime.onStartup.addListener(() => {
            this.handleStartup();
        });

        // Message handling
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // Keep message channel open for async responses
        });

        // Tab management
        chrome.tabs.onActivated.addListener((activeInfo) => {
            this.handleTabSwitch(activeInfo);
        });

        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            this.handleTabUpdate(tabId, changeInfo, tab);
        });

        // Context menu
        this.setupContextMenus();

        // Keyboard shortcuts
        chrome.commands.onCommand.addListener((command) => {
            this.handleCommand(command);
        });

        // Alarms for periodic tasks
        chrome.alarms.onAlarm.addListener((alarm) => {
            this.handleAlarm(alarm);
        });
    }

    async initializeStorage() {
        // Initialize default settings
        const defaultSettings = {
            autoProcess: true,
            voiceRecognition: true,
            suggestions: true,
            privacyMode: false,
            stealthMode: false,
            apiKey: '',
            selectedModel: 'gpt-4',
            confidenceThreshold: 0.8
        };

        const result = await chrome.storage.sync.get(['aiAssistantSettings']);
        if (!result.aiAssistantSettings) {
            await chrome.storage.sync.set({ aiAssistantSettings: defaultSettings });
        }

        // Initialize analytics
        const analyticsResult = await chrome.storage.local.get(['aiAssistantAnalytics']);
        if (!analyticsResult.aiAssistantAnalytics) {
            const defaultAnalytics = {
                meetingsCount: 0,
                tasksCount: 0,
                codeCount: 0,
                confidenceAvg: 0,
                totalInteractions: 0,
                successRate: 0,
                lastReset: Date.now()
            };
            await chrome.storage.local.set({ aiAssistantAnalytics: defaultAnalytics });
        }
    }

    async connectToAIBackend() {
        try {
            const response = await fetch(`${this.aiBackendUrl}/health`);
            if (response.ok) {
                this.isConnected = true;
                console.log('Connected to AI Backend');
                this.updateBadge('✓', '#4CAF50');
            } else {
                throw new Error('Backend not responding');
            }
        } catch (error) {
            console.warn('AI Backend not available:', error);
            this.isConnected = false;
            this.updateBadge('!', '#ff9800');
            
            // Retry connection in 30 seconds
            setTimeout(() => this.connectToAIBackend(), 30000);
        }
    }

    updateBadge(text, color) {
        chrome.action.setBadgeText({ text });
        chrome.action.setBadgeBackgroundColor({ color });
    }

    setupContextMenus() {
        // Clear existing menus
        chrome.contextMenus.removeAll(() => {
            // Create AI Assistant context menu
            chrome.contextMenus.create({
                id: 'ai-assistant-main',
                title: 'AI SDLC Assistant',
                contexts: ['selection', 'page']
            });

            chrome.contextMenus.create({
                id: 'analyze-selection',
                parentId: 'ai-assistant-main',
                title: 'Analyze Selection',
                contexts: ['selection']
            });

            chrome.contextMenus.create({
                id: 'create-task',
                parentId: 'ai-assistant-main',
                title: 'Create Task from Context',
                contexts: ['page', 'selection']
            });

            chrome.contextMenus.create({
                id: 'generate-code',
                parentId: 'ai-assistant-main',
                title: 'Generate Code Suggestion',
                contexts: ['selection']
            });

            chrome.contextMenus.create({
                id: 'separator1',
                parentId: 'ai-assistant-main',
                type: 'separator'
            });

            chrome.contextMenus.create({
                id: 'start-meeting-mode',
                parentId: 'ai-assistant-main',
                title: 'Start Meeting Mode',
                contexts: ['page']
            });

            chrome.contextMenus.create({
                id: 'toggle-stealth',
                parentId: 'ai-assistant-main',
                title: 'Toggle Stealth Mode',
                contexts: ['page']
            });
        });

        // Handle context menu clicks
        chrome.contextMenus.onClicked.addListener((info, tab) => {
            this.handleContextMenuClick(info, tab);
        });
    }

    async handleMessage(message, sender, sendResponse) {
        try {
            const { action, data } = message;

            switch (action) {
                case 'healthCheck':
                    sendResponse({ 
                        status: 'ok', 
                        connected: this.isConnected,
                        timestamp: Date.now()
                    });
                    break;

                case 'processContext':
                    const result = await this.processContext(data);
                    sendResponse({ success: true, result });
                    break;

                case 'toggleFeature':
                    this.toggleFeature(data.feature, data.enabled);
                    sendResponse({ success: true });
                    break;

                case 'updateAnalytics':
                    await this.updateAnalytics(data);
                    sendResponse({ success: true });
                    break;

                case 'getAIResponse':
                    const aiResponse = await this.getAIResponse(data);
                    sendResponse({ success: true, response: aiResponse });
                    break;

                case 'saveContextData':
                    await this.saveContextData(data);
                    sendResponse({ success: true });
                    break;

                default:
                    sendResponse({ error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Background message handling error:', error);
            sendResponse({ error: error.message });
        }
    }

    async processContext(contextData) {
        if (!this.isConnected) {
            throw new Error('AI Backend not connected');
        }

        try {
            const response = await fetch(`${this.aiBackendUrl}/api/ai-brain/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    context: contextData,
                    timestamp: Date.now(),
                    source: 'browser_extension'
                })
            });

            if (!response.ok) {
                throw new Error(`AI Backend error: ${response.status}`);
            }

            const result = await response.json();
            
            // Update session analytics
            this.sessionData.aiResponses++;
            this.sessionData.interactions++;
            
            return result;
        } catch (error) {
            console.error('Context processing error:', error);
            throw error;
        }
    }

    async getAIResponse(requestData) {
        if (!this.isConnected) {
            // Fallback to local processing
            return this.getLocalAIResponse(requestData);
        }

        try {
            const response = await fetch(`${this.aiBackendUrl}/api/ai-brain/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`AI Backend error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('AI response error:', error);
            return this.getLocalAIResponse(requestData);
        }
    }

    getLocalAIResponse(requestData) {
        // Simple local AI responses for offline mode
        const { type, context } = requestData;

        const responses = {
            'meeting': {
                suggestion: 'Consider taking notes on key decisions and action items.',
                confidence: 0.7,
                actions: ['Take notes', 'Track action items']
            },
            'task': {
                suggestion: 'This looks like it could be broken down into smaller tasks.',
                confidence: 0.6,
                actions: ['Create subtasks', 'Estimate effort']
            },
            'code': {
                suggestion: 'Consider adding error handling and documentation.',
                confidence: 0.8,
                actions: ['Add error handling', 'Write documentation']
            },
            'default': {
                suggestion: 'I can help analyze this content when connected to the AI backend.',
                confidence: 0.5,
                actions: ['Reconnect to backend']
            }
        };

        return responses[type] || responses['default'];
    }

    toggleFeature(feature, enabled) {
        if (enabled) {
            this.activeFeatures.add(feature);
        } else {
            this.activeFeatures.delete(feature);
        }

        // Notify all tabs about feature change
        this.broadcastToAllTabs({
            action: 'featureToggled',
            feature,
            enabled
        });
    }

    async updateAnalytics(analyticsData) {
        try {
            const result = await chrome.storage.local.get(['aiAssistantAnalytics']);
            const analytics = result.aiAssistantAnalytics || {};

            // Merge analytics data
            Object.assign(analytics, analyticsData);
            
            // Calculate averages and rates
            if (analytics.totalInteractions > 0) {
                analytics.successRate = Math.round(
                    (analytics.successfulInteractions || 0) / analytics.totalInteractions * 100
                );
            }

            await chrome.storage.local.set({ aiAssistantAnalytics: analytics });
        } catch (error) {
            console.error('Analytics update error:', error);
        }
    }

    async saveContextData(data) {
        try {
            // Save to local storage with timestamp
            const key = `context_${Date.now()}`;
            await chrome.storage.local.set({ [key]: data });

            // Clean up old context data (keep last 100 entries)
            const allData = await chrome.storage.local.get(null);
            const contextKeys = Object.keys(allData)
                .filter(key => key.startsWith('context_'))
                .sort((a, b) => {
                    const timeA = parseInt(a.split('_')[1]);
                    const timeB = parseInt(b.split('_')[1]);
                    return timeB - timeA;
                });

            if (contextKeys.length > 100) {
                const keysToRemove = contextKeys.slice(100);
                for (const key of keysToRemove) {
                    await chrome.storage.local.remove(key);
                }
            }
        } catch (error) {
            console.error('Context data save error:', error);
        }
    }

    async broadcastToAllTabs(message) {
        try {
            const tabs = await chrome.tabs.query({});
            for (const tab of tabs) {
                try {
                    await chrome.tabs.sendMessage(tab.id, message);
                } catch (error) {
                    // Tab might not have content script injected
                }
            }
        } catch (error) {
            console.error('Broadcast error:', error);
        }
    }

    handleTabSwitch(activeInfo) {
        this.sessionData.contextSwitches++;
        
        // Get tab info and detect platform
        chrome.tabs.get(activeInfo.tabId, (tab) => {
            if (tab && tab.url) {
                this.detectAndInjectIfNeeded(tab);
            }
        });
    }

    handleTabUpdate(tabId, changeInfo, tab) {
        if (changeInfo.status === 'complete' && tab.url) {
            this.detectAndInjectIfNeeded(tab);
        }
    }

    async detectAndInjectIfNeeded(tab) {
        const supportedDomains = [
            'meet.google.com',
            'atlassian.net',
            'github.com',
            'linear.app',
            'slack.com',
            'zoom.us',
            'teams.microsoft.com'
        ];

        const needsInjection = supportedDomains.some(domain => 
            tab.url.includes(domain)
        );

        if (needsInjection) {
            try {
                // Check if content script is already injected
                const response = await chrome.tabs.sendMessage(tab.id, { action: 'ping' });
                if (!response) {
                    // Inject content script
                    await chrome.scripting.executeScript({
                        target: { tabId: tab.id },
                        files: ['content_advanced.js']
                    });
                }
            } catch (error) {
                // Content script not injected, inject it
                try {
                    await chrome.scripting.executeScript({
                        target: { tabId: tab.id },
                        files: ['content_advanced.js']
                    });
                } catch (injectError) {
                    console.warn('Failed to inject content script:', injectError);
                }
            }
        }
    }

    async handleContextMenuClick(info, tab) {
        try {
            switch (info.menuItemId) {
                case 'analyze-selection':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'analyzeSelection',
                        text: info.selectionText
                    });
                    break;

                case 'create-task':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'createTaskFromContext',
                        context: info.pageUrl
                    });
                    break;

                case 'generate-code':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'generateCodeSuggestion',
                        text: info.selectionText
                    });
                    break;

                case 'start-meeting-mode':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'startMeetingMode'
                    });
                    break;

                case 'toggle-stealth':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'toggleStealthMode'
                    });
                    break;
            }
        } catch (error) {
            console.error('Context menu action error:', error);
        }
    }

    async handleCommand(command) {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            switch (command) {
                case 'activate-assistant':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'activateAssistant'
                    });
                    break;

                case 'toggle-stealth':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'toggleStealthMode'
                    });
                    break;

                case 'quick-analyze':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'quickAnalyze'
                    });
                    break;

                case 'create-task':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'createTaskFromContext'
                    });
                    break;

                case 'generate-code':
                    await chrome.tabs.sendMessage(tab.id, {
                        action: 'generateCodeSuggestion'
                    });
                    break;
            }
        } catch (error) {
            console.error('Command handling error:', error);
        }
    }

    handleInstall(details) {
        if (details.reason === 'install') {
            // First time install
            chrome.tabs.create({
                url: 'https://your-website.com/welcome'
            });
        } else if (details.reason === 'update') {
            // Extension updated
            this.updateBadge('NEW', '#2196F3');
            setTimeout(() => this.updateBadge('', ''), 5000);
        }
    }

    handleStartup() {
        // Reset session data
        this.sessionData = {
            startTime: Date.now(),
            interactions: 0,
            contextSwitches: 0,
            aiResponses: 0
        };
        
        // Reconnect to AI backend
        this.connectToAIBackend();
    }

    startPeriodicTasks() {
        // Set up periodic alarms
        chrome.alarms.create('healthCheck', { periodInMinutes: 5 });
        chrome.alarms.create('analyticsSync', { periodInMinutes: 15 });
        chrome.alarms.create('cleanup', { periodInMinutes: 60 });
    }

    async handleAlarm(alarm) {
        switch (alarm.name) {
            case 'healthCheck':
                if (!this.isConnected) {
                    this.connectToAIBackend();
                }
                break;

            case 'analyticsSync':
                await this.syncAnalytics();
                break;

            case 'cleanup':
                await this.cleanupStorage();
                break;
        }
    }

    async syncAnalytics() {
        try {
            if (this.isConnected) {
                const analytics = await chrome.storage.local.get(['aiAssistantAnalytics']);
                await fetch(`${this.aiBackendUrl}/api/analytics/sync`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        analytics: analytics.aiAssistantAnalytics,
                        session: this.sessionData
                    })
                });
            }
        } catch (error) {
            console.warn('Analytics sync failed:', error);
        }
    }

    async cleanupStorage() {
        try {
            // Clean up old context data
            const allData = await chrome.storage.local.get(null);
            const oldContextKeys = Object.keys(allData)
                .filter(key => key.startsWith('context_'))
                .filter(key => {
                    const timestamp = parseInt(key.split('_')[1]);
                    return Date.now() - timestamp > 7 * 24 * 60 * 60 * 1000; // 7 days
                });

            for (const key of oldContextKeys) {
                await chrome.storage.local.remove(key);
            }
        } catch (error) {
            console.error('Storage cleanup error:', error);
        }
    }
}

// Initialize background service
const backgroundService = new AdvancedBackgroundService();
