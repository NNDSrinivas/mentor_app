// Advanced AI SDLC Assistant Popup Script
class AdvancedPopup {
    constructor() {
        this.currentPlatform = null;
        this.connectionStatus = 'connecting';
        this.settings = {
            autoProcess: true,
            voiceRecognition: true,
            suggestions: true,
            privacyMode: false
        };
        this.analytics = {
            meetingsCount: 0,
            tasksCount: 0,
            codeCount: 0,
            confidenceAvg: 0
        };
        this.init();
    }

    async init() {
        await this.loadSettings();
        await this.loadAnalytics();
        this.setupEventListeners();
        this.updateUI();
        this.detectCurrentPlatform();
        this.checkConnection();
        
        // Start periodic updates
        setInterval(() => this.updateAnalytics(), 5000);
        setInterval(() => this.checkConnection(), 10000);
    }

    setupEventListeners() {
        // Feature cards
        document.querySelectorAll('.feature-card').forEach(card => {
            card.addEventListener('click', (e) => this.handleFeatureToggle(e));
        });

        // Quick action buttons
        document.getElementById('start-meeting-assistance').addEventListener('click', () => {
            this.executeAction('startMeetingAssistance');
        });

        document.getElementById('create-task-from-context').addEventListener('click', () => {
            this.executeAction('createTaskFromContext');
        });

        document.getElementById('generate-code-suggestion').addEventListener('click', () => {
            this.executeAction('generateCodeSuggestion');
        });

        document.getElementById('analyze-current-context').addEventListener('click', () => {
            this.executeAction('analyzeCurrentContext');
        });

        // Settings toggles
        document.querySelectorAll('.toggle-switch').forEach(toggle => {
            toggle.addEventListener('click', (e) => this.handleSettingToggle(e));
        });

        // Footer links
        document.getElementById('settings-link').addEventListener('click', () => {
            this.openSettings();
        });

        document.getElementById('help-link').addEventListener('click', () => {
            this.openHelp();
        });

        document.getElementById('feedback-link').addEventListener('click', () => {
            this.openFeedback();
        });

        // Upgrade banner
        document.getElementById('upgrade-banner').addEventListener('click', () => {
            this.openUpgrade();
        });
    }

    async loadSettings() {
        try {
            const result = await chrome.storage.sync.get(['aiAssistantSettings']);
            if (result.aiAssistantSettings) {
                this.settings = { ...this.settings, ...result.aiAssistantSettings };
            }
        } catch (error) {
            console.warn('Failed to load settings:', error);
        }
    }

    async saveSettings() {
        try {
            await chrome.storage.sync.set({ aiAssistantSettings: this.settings });
        } catch (error) {
            console.warn('Failed to save settings:', error);
        }
    }

    async loadAnalytics() {
        try {
            const result = await chrome.storage.local.get(['aiAssistantAnalytics']);
            if (result.aiAssistantAnalytics) {
                this.analytics = { ...this.analytics, ...result.aiAssistantAnalytics };
            }
        } catch (error) {
            console.warn('Failed to load analytics:', error);
        }
    }

    async saveAnalytics() {
        try {
            await chrome.storage.local.set({ aiAssistantAnalytics: this.analytics });
        } catch (error) {
            console.warn('Failed to save analytics:', error);
        }
    }

    async detectCurrentPlatform() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            const url = tab.url;
            
            let platform = 'unknown';
            let hostname;
            try {
                hostname = (new URL(url)).hostname;
            } catch (e) {
                hostname = '';
            }

            // Match directly on hostname or subdomain as appropriate
            if (hostname === 'meet.google.com') platform = 'meet';
            else if (hostname === 'atlassian.net' || hostname.endsWith('.atlassian.net') || hostname === 'jira' || hostname.endsWith('.jira')) platform = 'jira';
            else if (hostname === 'github.com' || hostname.endsWith('.github.com')) platform = 'github';
            else if (hostname === 'linear.app' || hostname.endsWith('.linear.app')) platform = 'linear';
            else if (hostname === 'slack.com' || hostname.endsWith('.slack.com')) platform = 'slack';
            else if (hostname === 'zoom.us' || hostname.endsWith('.zoom.us')) platform = 'zoom';
            else if (hostname === 'teams.microsoft.com' || hostname.endsWith('.teams.microsoft.com')) platform = 'teams';

            this.currentPlatform = platform;
            this.updatePlatformDisplay();
            
        } catch (error) {
            console.warn('Failed to detect platform:', error);
            document.getElementById('current-platform').textContent = 'Unknown';
        }
    }

    updatePlatformDisplay() {
        // Update current platform text
        const platformNames = {
            'meet': 'Google Meet',
            'jira': 'JIRA',
            'github': 'GitHub',
            'linear': 'Linear',
            'slack': 'Slack',
            'zoom': 'Zoom',
            'teams': 'MS Teams',
            'unknown': 'Web Page'
        };
        
        document.getElementById('current-platform').textContent = platformNames[this.currentPlatform] || 'Unknown';

        // Update platform badges
        document.querySelectorAll('.platform-badge').forEach(badge => {
            badge.classList.remove('active');
            if (badge.dataset.platform === this.currentPlatform) {
                badge.classList.add('active');
            }
        });
    }

    async checkConnection() {
        try {
            // Try to communicate with background script
            const response = await chrome.runtime.sendMessage({ 
                action: 'healthCheck',
                timestamp: Date.now()
            });
            
            if (response && response.status === 'ok') {
                this.connectionStatus = 'connected';
            } else {
                this.connectionStatus = 'warning';
            }
        } catch (error) {
            this.connectionStatus = 'offline';
        }
        
        this.updateConnectionStatus();
    }

    updateConnectionStatus() {
        const indicator = document.getElementById('connection-status');
        const text = document.getElementById('connection-text');
        
        indicator.className = `status-indicator ${this.connectionStatus}`;
        
        const statusTexts = {
            'connected': 'Connected',
            'connecting': 'Connecting...',
            'warning': 'Limited',
            'offline': 'Offline'
        };
        
        text.textContent = statusTexts[this.connectionStatus] || 'Unknown';
    }

    handleFeatureToggle(event) {
        const card = event.currentTarget;
        const feature = card.dataset.feature;
        
        // Toggle active state
        card.classList.toggle('active');
        
        // Send message to content script
        this.sendMessageToContentScript({
            action: 'toggleFeature',
            feature: feature,
            enabled: card.classList.contains('active')
        });
        
        // Provide user feedback
        this.showToast(`${feature} feature ${card.classList.contains('active') ? 'enabled' : 'disabled'}`);
    }

    handleSettingToggle(event) {
        const toggle = event.currentTarget;
        const settingId = toggle.id.replace('-toggle', '');
        
        // Toggle visual state
        toggle.classList.toggle('active');
        
        // Update settings
        const settingKey = this.camelCase(settingId);
        this.settings[settingKey] = toggle.classList.contains('active');
        
        // Save settings
        this.saveSettings();
        
        // Send to content script
        this.sendMessageToContentScript({
            action: 'updateSetting',
            setting: settingKey,
            value: this.settings[settingKey]
        });
    }

    async executeAction(action) {
        try {
            // Show loading state
            const button = event.target.closest('.action-button');
            const originalText = button.textContent;
            button.style.opacity = '0.6';
            button.textContent = 'Processing...';
            
            // Send action to content script
            const response = await this.sendMessageToContentScript({
                action: action,
                context: {
                    platform: this.currentPlatform,
                    timestamp: Date.now(),
                    settings: this.settings
                }
            });
            
            // Update analytics based on action
            if (action === 'startMeetingAssistance') {
                this.analytics.meetingsCount++;
            } else if (action === 'createTaskFromContext') {
                this.analytics.tasksCount++;
            } else if (action === 'generateCodeSuggestion') {
                this.analytics.codeCount++;
            }
            
            this.saveAnalytics();
            this.updateAnalyticsDisplay();
            
            // Restore button
            button.style.opacity = '1';
            button.textContent = originalText;
            
            // Show success
            this.showToast(`Action completed: ${action}`);
            
        } catch (error) {
            console.error('Action failed:', error);
            this.showToast('Action failed', 'error');
            
            // Restore button
            const button = event.target.closest('.action-button');
            button.style.opacity = '1';
        }
    }

    async sendMessageToContentScript(message) {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            return await chrome.tabs.sendMessage(tab.id, message);
        } catch (error) {
            console.warn('Failed to send message to content script:', error);
            throw error;
        }
    }

    async updateAnalytics() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            const response = await chrome.tabs.sendMessage(tab.id, {
                action: 'getAnalytics'
            });
            
            if (response && response.analytics) {
                this.analytics = { ...this.analytics, ...response.analytics };
                this.updateAnalyticsDisplay();
                this.saveAnalytics();
            }
        } catch (error) {
            // Silently fail - not critical
        }
    }

    updateAnalyticsDisplay() {
        document.getElementById('meetings-count').textContent = this.analytics.meetingsCount;
        document.getElementById('tasks-count').textContent = this.analytics.tasksCount;
        document.getElementById('code-count').textContent = this.analytics.codeCount;
        document.getElementById('confidence-avg').textContent = `${this.analytics.confidenceAvg}%`;
    }

    updateUI() {
        // Update settings toggles
        Object.entries(this.settings).forEach(([key, value]) => {
            const toggle = document.getElementById(`${this.kebabCase(key)}-toggle`);
            if (toggle) {
                toggle.classList.toggle('active', value);
            }
        });
        
        // Update analytics
        this.updateAnalyticsDisplay();
    }

    openSettings() {
        chrome.runtime.openOptionsPage();
    }

    openHelp() {
        chrome.tabs.create({
            url: 'https://github.com/your-repo/ai-sdlc-assistant/wiki'
        });
    }

    openFeedback() {
        chrome.tabs.create({
            url: 'https://github.com/your-repo/ai-sdlc-assistant/issues/new'
        });
    }

    openUpgrade() {
        chrome.tabs.create({
            url: 'https://your-website.com/upgrade'
        });
    }

    showToast(message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#f44336' : '#4CAF50'};
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 12px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        
        // Add to document
        document.body.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    // Utility functions
    camelCase(str) {
        return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
    }

    kebabCase(str) {
        return str.replace(/([A-Z])/g, '-$1').toLowerCase();
    }
}

// Initialize popup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AdvancedPopup();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
