// Popup JavaScript for AI Meeting Mentor Extension
class PopupController {
    constructor() {
        this.currentTab = null;
        this.meetingPlatform = null;
        this.monitoringActive = false;
        this.init();
    }

    async init() {
        await this.getCurrentTab();
        await this.detectMeetingPlatform();
        this.setupEventListeners();
        this.updateUI();
        this.loadSettings();
        this.startStatusUpdates();
    }

    async getCurrentTab() {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        this.currentTab = tab;
    }

    async detectMeetingPlatform() {
        if (!this.currentTab) return;

        const url = this.currentTab.url;
        if (url.includes('zoom.us')) {
            this.meetingPlatform = 'zoom';
        } else if (url.includes('teams.microsoft.com')) {
            this.meetingPlatform = 'teams';
        } else if (url.includes('meet.google.com')) {
            this.meetingPlatform = 'meet';
        } else if (url.includes('webex.com')) {
            this.meetingPlatform = 'webex';
        } else {
            this.meetingPlatform = null;
        }
    }

    setupEventListeners() {
        // Start/Stop Monitoring
        document.getElementById('startMonitoring').addEventListener('click', () => {
            this.toggleMonitoring();
        });

        // Ask Question
        document.getElementById('askQuestion').addEventListener('click', () => {
            this.toggleQuestionInput();
        });

        // Question Input
        const questionInput = document.getElementById('questionInput');
        questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.askQuestion(questionInput.value);
                questionInput.style.display = 'none';
                questionInput.value = '';
            }
        });

        // Toggle Overlay
        document.getElementById('toggleOverlay').addEventListener('click', () => {
            this.toggleOverlay();
        });

        // Open Dashboard
        document.getElementById('openDashboard').addEventListener('click', () => {
            this.openDashboard();
        });

        // Settings toggles
        document.getElementById('autoRespond').addEventListener('change', (e) => {
            this.saveSetting('autoRespond', e.target.checked);
        });

        document.getElementById('monitorChat').addEventListener('change', (e) => {
            this.saveSetting('monitorChat', e.target.checked);
        });

        document.getElementById('showOverlay').addEventListener('change', (e) => {
            this.saveSetting('showOverlay', e.target.checked);
        });

        document.getElementById('audioProcessing').addEventListener('change', (e) => {
            this.saveSetting('audioProcessing', e.target.checked);
        });

        // Recording controls
        document.getElementById('startRecording').addEventListener('click', () => {
            this.startRecording();
        });

        document.getElementById('stopRecording').addEventListener('click', () => {
            this.stopRecording();
        });

        // Resume upload
        document.getElementById('uploadResume').addEventListener('click', () => {
            document.getElementById('resumeFile').click();
        });

        document.getElementById('resumeFile').addEventListener('change', (e) => {
            this.handleResumeUpload(e);
        });
    }

    async toggleMonitoring() {
        if (!this.meetingPlatform) {
            this.showMessage('Please open a supported meeting platform first', 'error');
            return;
        }

        this.monitoringActive = !this.monitoringActive;
        
        try {
            // Send message to content script
            await chrome.tabs.sendMessage(this.currentTab.id, {
                action: this.monitoringActive ? 'startMonitoring' : 'stopMonitoring',
                platform: this.meetingPlatform
            });

            this.updateMonitoringButton();
            this.showMessage(
                this.monitoringActive ? 'Meeting monitoring started' : 'Meeting monitoring stopped',
                'success'
            );
        } catch (error) {
            console.error('Failed to toggle monitoring:', error);
            this.showMessage('Failed to toggle monitoring. Please refresh the page.', 'error');
        }
    }

    toggleQuestionInput() {
        const questionInput = document.getElementById('questionInput');
        const isVisible = questionInput.style.display !== 'none';
        
        questionInput.style.display = isVisible ? 'none' : 'block';
        if (!isVisible) {
            questionInput.focus();
        }
    }

    async askQuestion(question) {
        if (!question.trim()) return;

        try {
            // Check if we're on a meeting platform
            const isMeetingPlatform = this.meetingPlatform !== null;
            
            if (isMeetingPlatform) {
                // Send to content script if on meeting platform
                await chrome.tabs.sendMessage(this.currentTab.id, {
                    action: 'askQuestion',
                    question: question
                });
            } else {
                // Send to background script for direct API call
                const response = await chrome.runtime.sendMessage({
                    action: 'askQuestion',
                    question: question
                });
                
                if (response && response.success) {
                    this.addRecentResponse(question, response.data.response || 'Response received');
                } else {
                    throw new Error(response?.error || 'Failed to get response');
                }
            }

            this.showMessage('Question sent!', 'success');
        } catch (error) {
            console.error('Failed to ask question:', error);
            this.showMessage('Failed to send question', 'error');
        }
    }

    async toggleOverlay() {
        try {
            await chrome.tabs.sendMessage(this.currentTab.id, {
                action: 'toggleOverlay'
            });
            this.showMessage('Overlay toggled', 'success');
        } catch (error) {
            console.error('Failed to toggle overlay:', error);
            this.showMessage('Failed to toggle overlay', 'error');
        }
    }

    openDashboard() {
        chrome.tabs.create({ url: 'http://localhost:8082' });
    }

    updateUI() {
        const indicator = document.getElementById('meetingIndicator');
        const status = document.getElementById('meetingStatus');
        const platformInfo = document.getElementById('platformInfo');

        if (this.meetingPlatform) {
            indicator.className = 'indicator active';
            status.textContent = `Connected to ${this.meetingPlatform.toUpperCase()}`;
            platformInfo.textContent = `Ready to assist in ${this.meetingPlatform} meeting`;
        } else {
            indicator.className = 'indicator inactive';
            status.textContent = 'No meeting platform detected';
            platformInfo.textContent = 'Please open Zoom, Teams, Google Meet, or Webex';
        }

        this.updateMonitoringButton();
    }

    updateMonitoringButton() {
        const button = document.getElementById('startMonitoring');
        
        if (this.monitoringActive) {
            button.textContent = '⏹️ Stop Meeting Monitor';
            button.style.background = 'rgba(244, 67, 54, 0.3)';
        } else {
            button.textContent = '🎤 Start Meeting Monitor';
            button.style.background = 'rgba(76, 175, 80, 0.3)';
        }

        button.disabled = !this.meetingPlatform;
    }

    async loadSettings() {
        const result = await chrome.storage.sync.get([
            'autoRespond', 'monitorChat', 'showOverlay', 'audioProcessing'
        ]);

        document.getElementById('autoRespond').checked = result.autoRespond !== false;
        document.getElementById('monitorChat').checked = result.monitorChat !== false;
        document.getElementById('showOverlay').checked = result.showOverlay !== false;
        document.getElementById('audioProcessing').checked = result.audioProcessing === true;
    }

    async saveSetting(key, value) {
        await chrome.storage.sync.set({ [key]: value });
        
        // Notify content script of setting change
        try {
            await chrome.tabs.sendMessage(this.currentTab.id, {
                action: 'settingChanged',
                setting: key,
                value: value
            });
        } catch (error) {
            // Content script might not be loaded yet
            console.log('Could not notify content script of setting change');
        }
    }

    addRecentResponse(question, response) {
        const responsesList = document.getElementById('responsesList');
        const recentResponses = document.getElementById('recentResponses');
        
        recentResponses.style.display = 'block';
        
        const responseItem = document.createElement('div');
        responseItem.className = 'response-item';
        responseItem.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 4px;">Q: ${question}</div>
            <div>${response}</div>
        `;
        
        responsesList.insertBefore(responseItem, responsesList.firstChild);
        
        // Keep only the last 5 responses
        while (responsesList.children.length > 5) {
            responsesList.removeChild(responsesList.lastChild);
        }
    }

    startStatusUpdates() {
        // Check AI service health from storage every 2 seconds
        setInterval(async () => {
            try {
                // Check AI service health from background script storage
                const healthData = await chrome.storage.local.get(['serviceHealth']);
                this.updateAIStatus(healthData.serviceHealth);
                
                // Check content script monitoring status
                const response = await chrome.tabs.sendMessage(this.currentTab.id, {
                    action: 'getStatus'
                });
                
                if (response && response.monitoring !== undefined) {
                    this.monitoringActive = response.monitoring;
                    this.updateMonitoringButton();
                }
            } catch (error) {
                // Content script might not be loaded
            }
        }, 2000);
        
        // Initial health check
        this.checkAIStatus();
    }

    async checkAIStatus() {
        try {
            const healthData = await chrome.storage.local.get(['serviceHealth']);
            console.log('🔍 Popup checking AI status, got from storage:', healthData);
            this.updateAIStatus(healthData.serviceHealth);
        } catch (error) {
            console.error('Failed to check AI status:', error);
        }
    }

    updateAIStatus(healthData) {
        console.log('🔄 Updating AI status with data:', healthData);
        const statusElement = document.getElementById('aiStatus');
        const indicatorElement = document.getElementById('aiIndicator');
        
        if (statusElement && indicatorElement) {
            if (healthData && healthData.status === 'healthy') {
                statusElement.textContent = '🤖 AI Connected';
                statusElement.style.color = '#4CAF50';
                indicatorElement.className = 'indicator active';
                console.log('✅ UI updated to show AI Connected');
            } else {
                statusElement.textContent = '❌ AI Offline - Start mentor app';
                statusElement.style.color = '#f44336';
                indicatorElement.className = 'indicator inactive';
                console.log('❌ UI updated to show AI Offline, health data was:', healthData);
            }
        } else {
            console.error('❌ Could not find aiStatus or aiIndicator elements');
        }
    }

    showMessage(message, type) {
        // Create temporary message element
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#f44336' : '#4CAF50'};
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            z-index: 10000;
            font-size: 12px;
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            document.body.removeChild(messageDiv);
        }, 3000);
    }

    async startRecording() {
        try {
            console.log('🎬 Starting recording...');
            
            // Send message to background script to start recording
            const response = await chrome.runtime.sendMessage({
                action: 'startMeetingRecording'
            });

            if (response.success) {
                // Update UI
                document.getElementById('startRecording').style.display = 'none';
                document.getElementById('stopRecording').style.display = 'block';
                this.showMessage('🎬 Recording started!', 'success');
                console.log('✅ Recording started successfully');
            } else {
                throw new Error('Failed to start recording');
            }
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            this.showMessage('❌ Failed to start recording: ' + error.message, 'error');
        }
    }

    async stopRecording() {
        try {
            console.log('⏹️ Stopping recording...');
            
            // Send message to background script to stop recording
            const response = await chrome.runtime.sendMessage({
                action: 'stopMeetingRecording'
            });

            if (response.success) {
                // Update UI
                document.getElementById('startRecording').style.display = 'block';
                document.getElementById('stopRecording').style.display = 'none';
                this.showMessage('⏹️ Recording stopped!', 'success');
                console.log('✅ Recording stopped successfully');
            } else {
                throw new Error('Failed to stop recording');
            }
        } catch (error) {
            console.error('❌ Failed to stop recording:', error);
            this.showMessage('❌ Failed to stop recording: ' + error.message, 'error');
        }
    }

    async handleResumeUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            console.log('📄 Uploading resume:', file.name);
            this.showMessage('📄 Processing resume...', 'info');

            // Read file content
            const fileContent = await this.readFileContent(file);
            
            // Send to background script for processing
            const response = await chrome.runtime.sendMessage({
                action: 'uploadResume',
                data: {
                    fileName: file.name,
                    content: fileContent,
                    fileType: file.type
                }
            });

            if (response.success) {
                document.getElementById('resumeStatus').style.display = 'block';
                this.showMessage('✅ Resume uploaded successfully!', 'success');
                console.log('✅ Resume processed and stored');
            } else {
                throw new Error(response.error || 'Failed to process resume');
            }

        } catch (error) {
            console.error('❌ Resume upload failed:', error);
            this.showMessage('❌ Failed to upload resume: ' + error.message, 'error');
        }
    }

    async readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                resolve(e.target.result);
            };
            
            reader.onerror = () => {
                reject(new Error('Failed to read file'));
            };

            // Read as text for most formats
            if (file.type.includes('text') || file.name.endsWith('.txt')) {
                reader.readAsText(file);
            } else {
                // For PDF and DOC files, read as data URL (base64)
                reader.readAsDataURL(file);
            }
        });
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PopupController();
});
