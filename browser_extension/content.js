// AI Interview Assistant - Minimal Clean Version
// Focus: Microphone access and basic functionality

console.log('🤖 AI Interview Assistant Loading...');

// Add immediate test div to verify script loading
const testDiv = document.createElement('div');
testDiv.style.cssText = `
    position: fixed !important;
    top: 10px !important;
    left: 10px !important;
    background: red !important;
    color: white !important;
    padding: 10px !important;
    z-index: 999999 !important;
    font-size: 12px !important;
`;
testDiv.textContent = 'AI Extension Loading...';
document.body.appendChild(testDiv);

setTimeout(() => {
    if (testDiv && testDiv.parentNode) {
        testDiv.parentNode.removeChild(testDiv);
    }
}, 3000);

class AIInterviewAssistant {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.overlay = null;
        this.offscreenWindow = null;
        this.stealthIndicator = null;
        this.isStealthMode = false;
        
        console.log('🤖 AI Interview Assistant initialized');
    }

    initialize() {
        console.log('🔧 Initializing AI Interview Assistant...');
        
        // Add a simple test indicator first
        this.addTestIndicator();
        
        // Initialize speech recognition
        this.initializeSpeechRecognition();
        
        // Create main overlay
        this.createOverlay();
        
        // Check backend connection
        this.checkBackend();
        
        // Set up hotkeys for stealth mode
        this.setupHotkeys();
        
        // Set up message listener for offscreen communication
        window.addEventListener('message', (event) => {
            this.handleOffscreenMessage(event);
        });
        
        console.log('✅ AI Interview Assistant fully initialized');
    }

    setupHotkeys() {
        // Set up Ctrl+Shift+H for emergency stealth toggle
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'H') {
                e.preventDefault();
                this.toggleStealth();
                console.log('🔍 Manual stealth mode toggled via hotkey');
            }
        });
    }

    toggleStealth() {
        if (this.isStealthMode) {
            this.deactivateFullStealth();
        } else {
            this.activateFullStealth();
        }
        this.isStealthMode = !this.isStealthMode;
    }

    initializeSpeechRecognition() {
        // Initialize speech recognition (existing method)
        this.setupSpeechRecognition();
    }

    async checkBackend() {
        // Check if backend is running
        try {
            const response = await fetch('http://localhost:8084/api/health');
            if (response.ok) {
                this.updateStatus('✅ AI Connected and Ready');
                this.loadSavedResume();
            } else {
                this.updateStatus('❌ AI Backend Offline');
            }
        } catch (error) {
            this.updateStatus('❌ Start the mentor app backend');
        }
    }

    async loadSavedResume() {
        try {
            const response = await fetch('http://localhost:8084/api/resume/status');
            if (response.ok) {
                const data = await response.json();
                if (data.has_resume) {
                    this.updateResumeStatus(`✅ Resume loaded: ${data.word_count} words`);
                }
            }
        } catch (error) {
            console.log('ℹ️ No saved resume found');
        }
    }

    addTestIndicator() {
        // Add a very visible test indicator to confirm the extension is working
        const testDiv = document.createElement('div');
        testDiv.id = 'ai-test-indicator';
        testDiv.style.cssText = `
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            background: red !important;
            color: white !important;
            padding: 20px !important;
            z-index: 2147483647 !important;
            font-family: Arial, sans-serif !important;
            font-size: 16px !important;
            border-radius: 10px !important;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.8) !important;
            text-align: center !important;
            border: 3px solid white !important;
        `;
        testDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px;">🤖 AI ASSISTANT ACTIVE!</div>
            <div style="font-size: 12px;">Extension loaded successfully</div>
            <div style="font-size: 10px; margin-top: 8px; color: #ffcccc;">This will disappear in 3 seconds</div>
        `;
        
        document.body.appendChild(testDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (testDiv.parentNode) {
                testDiv.remove();
            }
        }, 3000);
        
        console.log('🚨 Test indicator added - you should see a red popup in the center of the screen');
    }

    async init() {
        try {
            // Create overlay first
            this.createOverlay();
            
            // Check AI connection
            await this.checkAIConnection();
            
            // Check resume status
            await this.checkResumeStatus();
            
            // Request microphone permission and start listening
            await this.startListening();
            
        } catch (error) {
            console.error('❌ Initialization failed:', error);
            this.updateStatus('❌ Initialization failed');
        }
    }

    createOverlay() {
        // Remove existing overlay
        const existing = document.getElementById('ai-assistant-overlay');
        if (existing) existing.remove();

        // Create overlay with maximum visibility
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-assistant-overlay';
        
        // Apply styles directly to ensure visibility
        this.overlay.style.position = 'fixed';
        this.overlay.style.top = '20px';
        this.overlay.style.right = '20px';
        this.overlay.style.width = '380px';
        this.overlay.style.maxHeight = '90vh';
        this.overlay.style.background = 'rgba(0, 0, 0, 0.95)';
        this.overlay.style.color = '#00ff00';
        this.overlay.style.fontFamily = 'monospace';
        this.overlay.style.fontSize = '11px';
        this.overlay.style.border = '2px solid #00ff00';
        this.overlay.style.borderRadius = '10px';
        this.overlay.style.zIndex = '2147483647';
        this.overlay.style.padding = '12px';
        this.overlay.style.boxShadow = '0 0 20px rgba(0, 255, 0, 0.5)';
        this.overlay.style.overflowY = 'auto';
        this.overlay.style.display = 'block';
        this.overlay.style.visibility = 'visible';
        this.overlay.style.opacity = '1';
        this.overlay.style.pointerEvents = 'auto';
        
        this.overlay.innerHTML = `
            <div style="text-align: center; margin-bottom: 12px; color: #00ff00; font-weight: bold; font-size: 14px;">
                🤖 AI Interview Assistant (Private)
            </div>
            
            <div style="text-align: center; margin-bottom: 8px; font-size: 10px; color: #ff8c00; border: 1px solid #ff8c00; padding: 4px; border-radius: 3px; background: rgba(255, 140, 0, 0.1);">
                🔒 Private View - Not shared with participants
            </div>
            
            <div id="status" style="
                text-align: center;
                padding: 8px;
                background: rgba(0, 255, 0, 0.1);
                border: 1px solid #00ff00;
                border-radius: 5px;
                margin-bottom: 12px;
                font-size: 10px;
            ">
                🔧 Initializing...
            </div>
            
            <div id="resume-section" style="
                background: rgba(255, 165, 0, 0.1);
                border: 1px solid #ff8c00;
                border-radius: 5px;
                padding: 8px;
                margin-bottom: 12px;
            ">
                <div style="margin-bottom: 8px; font-weight: bold; text-align: center; color: #ff8c00; font-size: 11px;">
                    📄 Smart Resume Upload
                </div>
                <div id="resume-status" style="text-align: center; margin-bottom: 8px; font-size: 9px;">
                    No resume uploaded
                </div>
                
                <!-- File Upload Option -->
                <div style="margin-bottom: 8px;">
                    <input type="file" id="resume-file" accept=".txt,.pdf,.doc,.docx" style="
                        width: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        color: #00ff00;
                        border: 1px solid #00ff00;
                        border-radius: 3px;
                        padding: 4px;
                        font-family: monospace;
                        font-size: 9px;
                        margin-bottom: 4px;
                        box-sizing: border-box;
                    ">
                    <div style="text-align: center; font-size: 8px; color: #666; margin-bottom: 6px;">
                        Best: TXT files | PDF/DOC: Copy text and use Text Input option
                    </div>
                </div>
                
                <!-- OR Divider -->
                <div style="text-align: center; margin: 6px 0; color: #666; font-size: 8px;">
                    — OR —
                </div>
                
                <!-- Text Input Option (Collapsed by default) -->
                <div id="text-input-section" style="display: none;">
                    <textarea id="resume-text" placeholder="Paste your comprehensive resume here (supports 15+ pages, 5000+ words)..." style="
                        width: 100%;
                        height: 80px;
                        background: rgba(0, 0, 0, 0.5);
                        color: #00ff00;
                        border: 1px solid #00ff00;
                        border-radius: 3px;
                        padding: 6px;
                        font-family: monospace;
                        font-size: 8px;
                        resize: vertical;
                        margin-bottom: 6px;
                        max-height: 120px;
                        overflow-y: auto;
                        box-sizing: border-box;
                    "></textarea>
                    <div style="text-align: center; font-size: 8px; color: #666; margin-bottom: 6px;">
                        Large resumes supported - AI will memorize all content
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <button id="upload-resume" style="
                        background: #ff8c00;
                        color: black;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 9px;
                        margin: 2px;
                    ">📤 Upload</button>
                    <button id="toggle-text-input" style="
                        background: #444;
                        color: #ff8c00;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 9px;
                        margin: 2px;
                    ">📝 Text</button>
                    <button id="clear-resume" style="
                        background: #666;
                        color: white;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 3px;
                        cursor: pointer;
                        font-size: 9px;
                        margin: 2px;
                    ">🗑️ Clear</button>
                </div>
            </div>
            
            <div id="question-area" style="
                background: rgba(0, 100, 255, 0.1);
                border: 1px solid #0066ff;
                border-radius: 5px;
                padding: 8px;
                margin-bottom: 12px;
                min-height: 30px;
                display: none;
                font-size: 9px;
            ">
                <strong>Question:</strong> <span id="question-text"></span>
            </div>
            
            <div id="answer-area" style="
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid #00ff00;
                border-radius: 5px;
                padding: 10px;
                height: 200px;
                overflow-y: auto;
                line-height: 1.4;
                font-size: 9px;
            ">
                <div style="text-align: center; color: #666; padding: 30px 0;">
                    🎤 Ready to listen for interview questions
                    <br><br>
                    <button id="test-btn" style="
                        background: #00ff00;
                        color: black;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 8px;
                        font-size: 9px;
                    ">Test Connection</button>
                </div>
            </div>
            
            <div style="margin-top: 10px; text-align: center;">
                <button id="toggle-listen" style="
                    background: #00ff00;
                    color: black;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 10px;
                    margin-right: 8px;
                ">🎤 Start Listening</button>
                <button id="stealth-toggle" style="
                    background: #ff6600;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 9px;
                ">🫥 Stealth Mode</button>
            </div>
        `;

        document.body.appendChild(this.overlay);
        
        // Force visibility immediately
        this.overlay.style.display = 'block';
        this.overlay.style.visibility = 'visible';
        this.overlay.style.opacity = '1';
        
        // Add stealth mode indicator
        this.addStealthIndicator();
        
        // Add event listeners
        const testBtn = document.getElementById('test-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.testConnection();
            });
        }
        
        const toggleListenBtn = document.getElementById('toggle-listen');
        if (toggleListenBtn) {
            toggleListenBtn.addEventListener('click', () => {
                this.toggleListening();
            });
        }

        const stealthToggleBtn = document.getElementById('stealth-toggle');
        if (stealthToggleBtn) {
            stealthToggleBtn.addEventListener('click', () => {
                this.toggleStealth();
            });
        }

        // Resume functionality event listeners
        const uploadResumeBtn = document.getElementById('upload-resume');
        if (uploadResumeBtn) {
            uploadResumeBtn.addEventListener('click', () => {
                this.uploadResume();
            });
        }

        const toggleTextInputBtn = document.getElementById('toggle-text-input');
        if (toggleTextInputBtn) {
            toggleTextInputBtn.addEventListener('click', () => {
                this.toggleTextInput();
            });
        }

        const clearResumeBtn = document.getElementById('clear-resume');
        if (clearResumeBtn) {
            clearResumeBtn.addEventListener('click', () => {
                this.clearResume();
            });
        }

        // File input change handler
        const resumeFileInput = document.getElementById('resume-file');
        if (resumeFileInput) {
            resumeFileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e);
            });
        }

        console.log('✅ Simplified overlay created and should be visible');
        
        // Add helpful instructions
        console.log('🔒 CONTROLS:');
        console.log('   • Click "Stealth Mode" button to hide from screen sharing');
        console.log('   • Press Ctrl+Shift+H for emergency stealth toggle');
        console.log('   • Look for red dot when in stealth mode');
    }

    addPrivacyCSS() {
        // Inject advanced privacy CSS to hide from screen sharing
        const style = document.createElement('style');
        style.textContent = `
            #ai-assistant-overlay {
                /* Basic positioning and visibility */
                position: fixed !important;
                top: 20px !important;
                right: 20px !important;
                z-index: 2147483647 !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                
                /* Screen capture blocking techniques */
                contain: layout style paint !important;
                isolation: isolate !important;
                will-change: transform, opacity !important;
                
                /* Advanced privacy layers */
                mix-blend-mode: normal !important;
                filter: none !important;
                backdrop-filter: none !important;
                
                /* Prevent text selection and interactions */
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                user-select: none !important;
                -webkit-touch-callout: none !important;
                -webkit-tap-highlight-color: transparent !important;
                
                /* Transform layers for privacy */
                transform: translateZ(0) translate3d(0,0,0) !important;
                -webkit-transform: translateZ(0) translate3d(0,0,0) !important;
                transform-style: preserve-3d !important;
                -webkit-transform-style: preserve-3d !important;
            }
            
            /* Hide from all media types that aren't screen */
            @media print {
                #ai-assistant-overlay { display: none !important; }
            }
            
            @media screen and (max-width: 0) {
                #ai-assistant-overlay { display: none !important; }
            }
            
            /* Additional screen sharing privacy */
            #ai-assistant-overlay::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
                z-index: -1;
                background: transparent;
                mix-blend-mode: multiply;
            }
        `;
        
        document.head.appendChild(style);
        
        // Add screen sharing detection
        this.setupScreenShareDetection();
        
        console.log('🔒 Advanced privacy system activated');
    }

    setupScreenShareDetection() {
        // Monitor for screen sharing and completely hide overlay
        let isScreenSharing = false;
        let overlayBackup = null;
        
        // Detect screen sharing through getDisplayMedia API monitoring
        const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia;
        if (originalGetDisplayMedia) {
            const self = this;
            navigator.mediaDevices.getDisplayMedia = function(...args) {
                console.log('🖥️ Screen sharing detected via API - full stealth mode');
                isScreenSharing = true;
                self.activateFullStealth();
                return originalGetDisplayMedia.apply(this, args);
            };
        }
        
        // Monitor for Google Meet screen sharing UI changes
        const meetObserver = new MutationObserver((mutations) => {
            // Look for screen sharing indicators in Google Meet
            const presentButton = document.querySelector('[data-tooltip*="present"], [aria-label*="Present"], button[aria-label*="present"]');
            const screenShareActive = document.querySelector('[data-is-presenting="true"], .presenting-indicator, [aria-pressed="true"][aria-label*="present"]');
            const shareScreenText = document.body.textContent.includes('Stop sharing') || document.body.textContent.includes('You are presenting');
            
            // Check URL for screen sharing indicators
            const urlHasScreenShare = window.location.href.includes('screenshare') || window.location.href.includes('present');
            
            if (screenShareActive || shareScreenText || urlHasScreenShare) {
                if (!isScreenSharing) {
                    console.log('🖥️ Google Meet screen sharing detected - activating full stealth');
                    isScreenSharing = true;
                    this.activateFullStealth();
                }
            } else if (isScreenSharing && !shareScreenText) {
                console.log('🖥️ Screen sharing ended - restoring overlay');
                isScreenSharing = false;
                this.deactivateFullStealth();
            }
        });
        
        meetObserver.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-is-presenting', 'aria-label', 'aria-pressed']
        });
        
        // Monitor page title for screen sharing indicators
        const titleObserver = new MutationObserver(() => {
            const title = document.title;
            if (title.includes('Presenting') || title.includes('Screen share')) {
                if (!isScreenSharing) {
                    console.log('🖥️ Screen sharing detected via title - full stealth');
                    isScreenSharing = true;
                    this.activateFullStealth();
                }
            }
        });
        
        titleObserver.observe(document.querySelector('title'), {
            childList: true
        });
        
        // Manual stealth toggle for emergency (Ctrl+Shift+H)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'H') {
                isScreenSharing = !isScreenSharing;
                if (isScreenSharing) {
                    this.activateFullStealth();
                } else {
                    this.deactivateFullStealth();
                }
                console.log(`🔍 Manual stealth mode: ${isScreenSharing ? 'ON (HIDDEN)' : 'OFF (VISIBLE)'}`);
            }
        });
        
        // Auto-detect when sharing starts by monitoring browser tab visibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Tab might be hidden due to screen sharing
                setTimeout(() => {
                    if (document.hidden) {
                        console.log('🖥️ Tab hidden - possible screen share - activating stealth');
                        if (!isScreenSharing) {
                            isScreenSharing = true;
                            this.activateFullStealth();
                        }
                    }
                }, 1000);
            }
        });
    }

    activateFullStealth() {
        if (this.overlay && this.overlay.parentNode) {
            console.log('🫥 STEALTH MODE: Moving to separate window (invisible to screen capture)');
            
            // FIRST: Hide the main overlay completely from the meeting tab
            this.overlay.style.cssText = `
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                transform: translateX(-9999px) !important;
            `;
            
            // THEN: Create the separate popup window
            this.createOffscreenWindow();
            
            // Update stealth indicator
            if (this.stealthIndicator) {
                this.stealthIndicator.style.display = 'block';
                this.stealthIndicator.style.background = '#ff0000';
                this.stealthIndicator.title = 'AI Assistant - STEALTH MODE (Moved to separate window)';
            }
            
            console.log('🎭 Stealth mode: Main overlay hidden, popup window opened');
        }
    }

    deactivateFullStealth() {
        if (this.overlay) {
            console.log('👁️ NORMAL MODE: Back to main tab');
            
            // Close offscreen window if it exists
            if (this.offscreenWindow && !this.offscreenWindow.closed) {
                this.offscreenWindow.close();
                this.offscreenWindow = null;
            }
            
            // Restore the main overlay in the meeting tab with full visibility
            this.overlay.style.cssText = `
                position: fixed !important;
                top: 20px !important;
                right: 20px !important;
                width: 380px !important;
                max-height: 90vh !important;
                background: rgba(0, 0, 0, 0.95) !important;
                color: #00ff00 !important;
                font-family: monospace !important;
                font-size: 11px !important;
                border: 2px solid #00ff00 !important;
                border-radius: 10px !important;
                z-index: 2147483647 !important;
                padding: 12px !important;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.5) !important;
                overflow-y: auto !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                transform: none !important;
            `;
            
            // Hide stealth indicator
            if (this.stealthIndicator) {
                this.stealthIndicator.style.display = 'none';
            }
            
            console.log('✨ Normal mode: Main overlay restored and visible');
        }
    }

    createOffscreenWindow() {
        // Create a separate popup window for the AI assistant during screen sharing
        const windowFeatures = 'width=400,height=600,top=100,left=100,toolbar=no,menubar=no,scrollbars=yes,resizable=yes';
        
        try {
            this.offscreenWindow = window.open('', 'AIAssistantOffscreen', windowFeatures);
            
            if (this.offscreenWindow) {
                // Clone the overlay content to the new window
                this.offscreenWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>AI Interview Assistant (Private)</title>
                        <style>
                            body {
                                margin: 0;
                                background: #000;
                                font-family: monospace;
                                overflow: hidden;
                            }
                            #offscreen-overlay {
                                position: fixed;
                                top: 0;
                                left: 0;
                                right: 0;
                                bottom: 0;
                                background: rgba(0, 0, 0, 0.95);
                                color: #00ff00;
                                font-size: 11px;
                                border: 2px solid #00ff00;
                                padding: 12px;
                                box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
                                overflow-y: auto;
                            }
                            
                            /* Privacy header */
                            .privacy-header {
                                text-align: center;
                                margin-bottom: 12px;
                                color: #ff0000;
                                font-weight: bold;
                                font-size: 14px;
                                background: rgba(255, 0, 0, 0.1);
                                border: 1px solid #ff0000;
                                padding: 8px;
                                border-radius: 5px;
                            }
                            
                            .status-section {
                                text-align: center;
                                padding: 8px;
                                background: rgba(0, 255, 0, 0.1);
                                border: 1px solid #00ff00;
                                border-radius: 5px;
                                margin-bottom: 12px;
                                font-size: 10px;
                            }
                            
                            button {
                                background: #00ff00;
                                color: black;
                                border: none;
                                padding: 8px 16px;
                                border-radius: 5px;
                                cursor: pointer;
                                font-weight: bold;
                                font-size: 10px;
                                margin: 5px;
                            }
                            
                            button:hover {
                                background: #00cc00;
                            }
                            
                            #answer-display {
                                background: rgba(0, 0, 0, 0.5);
                                border: 1px solid #00ff00;
                                border-radius: 5px;
                                padding: 10px;
                                height: 300px;
                                overflow-y: auto;
                                line-height: 1.4;
                                font-size: 9px;
                                margin-top: 10px;
                            }
                        </style>
                    </head>
                    <body>
                        <div id="offscreen-overlay">
                            <div class="privacy-header">
                                🔒 AI Interview Assistant - STEALTH MODE
                                <br><small>This window is NOT visible in screen sharing</small>
                            </div>
                            
                            <div class="status-section" id="offscreen-status">
                                🎭 Stealth mode active - Ready for questions
                            </div>
                            
                            <div style="text-align: center;">
                                <button onclick="testConnection()">🧪 Test AI</button>
                                <button onclick="returnToMainTab()">↩️ Return to Main Tab</button>
                            </div>
                            
                            <div id="answer-display">
                                <div style="text-align: center; color: #666; padding: 50px 0;">
                                    🎤 Listening for questions in main tab...
                                    <br><br>
                                    This window stays private during screen sharing
                                </div>
                            </div>
                        </div>
                        
                        <script>
                            function testConnection() {
                                // Communicate with main tab
                                if (window.opener && !window.opener.closed) {
                                    window.opener.postMessage({
                                        type: 'ai-test-connection'
                                    }, '*');
                                }
                            }
                            
                            function returnToMainTab() {
                                // Tell main tab to exit stealth mode
                                if (window.opener && !window.opener.closed) {
                                    window.opener.postMessage({
                                        type: 'ai-exit-stealth'
                                    }, '*');
                                }
                                window.close();
                            }
                            
                            // Listen for updates from main tab
                            window.addEventListener('message', function(event) {
                                if (event.data.type === 'ai-update-answer') {
                                    document.getElementById('answer-display').innerHTML = event.data.content;
                                } else if (event.data.type === 'ai-update-status') {
                                    document.getElementById('offscreen-status').textContent = event.data.status;
                                }
                            });
                            
                            // Keep window alive
                            window.addEventListener('beforeunload', function() {
                                if (window.opener && !window.opener.closed) {
                                    window.opener.postMessage({
                                        type: 'ai-offscreen-closed'
                                    }, '*');
                                }
                            });
                        </script>
                    </body>
                    </html>
                `);
                
                this.offscreenWindow.document.close();
                
                // Focus the offscreen window
                this.offscreenWindow.focus();
                
                console.log('✅ Offscreen window created and focused');
            } else {
                console.warn('⚠️ Could not create offscreen window (popup blocked?)');
                // Fallback: just hide the overlay
                this.overlay.style.opacity = '0.1';
            }
        } catch (error) {
            console.error('❌ Failed to create offscreen window:', error);
            // Fallback: just hide the overlay
            this.overlay.style.opacity = '0.1';
        }
    }

    addStealthIndicator() {
        // Add a small stealth mode indicator
        const stealthIndicator = document.createElement('div');
        stealthIndicator.id = 'stealth-mode-indicator';
        stealthIndicator.style.cssText = `
            position: fixed !important;
            top: 5px !important;
            right: 5px !important;
            width: 12px !important;
            height: 12px !important;
            background: #00ff00 !important;
            border-radius: 50% !important;
            z-index: 2147483646 !important;
            display: none !important;
            box-shadow: 0 0 4px rgba(0, 255, 0, 0.5) !important;
        `;
        stealthIndicator.title = 'AI Assistant - Stealth Mode';
        document.body.appendChild(stealthIndicator);
        
        // Show indicator when stealth mode is active
        this.stealthIndicator = stealthIndicator;
    }

    async checkAIConnection() {
        try {
            this.updateStatus('🔗 Checking AI connection...');
            
            const response = await fetch('http://localhost:8084/api/health');
            if (response.ok) {
                this.updateStatus('✅ AI Connected');
                console.log('✅ AI service connected');
                return true;
            } else {
                throw new Error('AI service not responding');
            }
        } catch (error) {
            this.updateStatus('❌ AI Offline - Start mentor app');
            console.error('❌ AI connection failed:', error);
            return false;
        }
    }

    async startListening() {
        try {
            this.updateStatus('🎤 Requesting microphone access...');
            
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            console.log('✅ Microphone permission granted');
            
            // Stop the test stream
            stream.getTracks().forEach(track => track.stop());
            
            // Set up speech recognition
            await this.setupSpeechRecognition();
            
        } catch (error) {
            console.error('❌ Microphone access failed:', error);
            this.updateStatus('❌ Microphone access denied');
            
            // Show manual test button instead
            document.getElementById('toggle-listen').style.display = 'none';
        }
    }

    async setupSpeechRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('❌ Speech recognition not supported');
            this.updateStatus('❌ Speech recognition not supported');
            return;
        }

        try {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            // Configuration
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            // Event handlers
            this.recognition.onstart = () => {
                console.log('🎤 Speech recognition started');
                this.updateStatus('🎤 Listening for questions...');
                this.isListening = true;
                document.getElementById('toggle-listen').textContent = '⏹️ Stop Listening';
            };
            
            this.recognition.onresult = (event) => {
                this.handleSpeechResult(event);
            };
            
            this.recognition.onerror = (event) => {
                console.log('🎤 Speech recognition error:', event.error);
                
                if (event.error === 'not-allowed') {
                    this.updateStatus('❌ Microphone permission denied');
                    return;
                }
                
                if (event.error === 'no-speech') {
                    console.log('🔇 No speech detected - continuing...');
                    return;
                }
                
                this.updateStatus(`⚠️ Speech error: ${event.error}`);
            };
            
            this.recognition.onend = () => {
                console.log('🎤 Speech recognition ended');
                if (this.isListening) {
                    // Restart if we should still be listening
                    setTimeout(() => {
                        if (this.recognition && this.isListening) {
                            this.recognition.start();
                        }
                    }, 100);
                } else {
                    this.updateStatus('🔇 Stopped listening');
                    document.getElementById('toggle-listen').textContent = '🎤 Start Listening';
                }
            };
            
            this.updateStatus('✅ Ready to listen');
            console.log('✅ Speech recognition ready');
            
        } catch (error) {
            console.error('❌ Speech recognition setup failed:', error);
            this.updateStatus('❌ Speech recognition failed');
        }
    }

    handleSpeechResult(event) {
        let finalTranscript = '';
        
        // Get final transcript
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            }
        }
        
        if (finalTranscript.trim()) {
            console.log('🎯 Speech detected:', finalTranscript);
            
            // Simple question detection
            if (this.isQuestion(finalTranscript)) {
                console.log('❓ Question detected:', finalTranscript);
                this.processQuestion(finalTranscript);
            } else {
                console.log('💬 Speech (not a question):', finalTranscript);
            }
        }
    }

    isQuestion(text) {
        const questionWords = ['what', 'how', 'why', 'when', 'where', 'who', 'tell me', 'describe', 'explain'];
        const lowerText = text.toLowerCase();
        
        return questionWords.some(word => lowerText.includes(word)) || text.trim().endsWith('?');
    }

    async processQuestion(question) {
        try {
            console.log('🎯 Processing question:', question);
            
            // Show the question immediately
            const questionArea = document.getElementById('question-area');
            const questionText = document.getElementById('question-text');
            if (questionArea && questionText) {
                questionArea.style.display = 'block';
                questionText.textContent = question;
            }
            
            this.updateStatus('🧠 AI is thinking...');
            
            // Get AI response
            const response = await fetch('http://localhost:8084/api/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    interview_mode: true
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.displayAnswer(data.response, question);
                this.updateStatus('✅ Answer ready - Read it back!');
            } else {
                throw new Error(`API error: ${response.status}`);
            }

        } catch (error) {
            console.error('❌ Failed to process question:', error);
            this.displayAnswer('❌ Sorry, I could not process that question. Please check the AI service.', question);
            this.updateStatus('❌ Error processing question');
        }
    }

    handleOffscreenMessage(event) {
        // Handle messages from the offscreen window
        if (event.data.type === 'ai-test-connection') {
            console.log('🧪 Test connection request from offscreen window');
            this.testConnection();
        } else if (event.data.type === 'ai-exit-stealth') {
            console.log('↩️ Exit stealth mode request from offscreen window');
            this.deactivateFullStealth();
        } else if (event.data.type === 'ai-offscreen-closed') {
            console.log('🪟 Offscreen window closed');
            this.offscreenWindow = null;
            // Automatically exit stealth mode if window is closed
            this.deactivateFullStealth();
        }
    }

    displayAnswer(answer, question) {
        // Show the question area with the current question
        const questionArea = document.getElementById('question-area');
        const questionText = document.getElementById('question-text');
        if (questionArea && questionText) {
            questionArea.style.display = 'block';
            questionText.textContent = question;
        }

        // Display the answer in a readable format
        const answerContent = `
            <div style="margin-bottom: 15px; background: rgba(0, 100, 255, 0.1); padding: 8px; border-radius: 5px;">
                <strong style="color: #0066ff;">❓ Question:</strong><br>
                <span style="color: #white; font-size: 10px;">${question}</span>
            </div>
            <div style="background: rgba(0, 255, 0, 0.1); padding: 10px; border-radius: 5px; border-left: 3px solid #00ff00;">
                <strong style="color: #00ff00; font-size: 11px;">💡 Your Answer:</strong><br><br>
                <div style="color: #00ff00; line-height: 1.6; font-size: 10px;">
                    ${answer.replace(/\n/g, '<br>')}
                </div>
            </div>
            <div style="margin-top: 15px; text-align: center; font-size: 10px; color: #666; border-top: 1px solid #333; padding-top: 8px;">
                📋 <strong>Read this answer back to the interviewer</strong> 📋<br>
                <small>Ready for next question...</small>
            </div>
        `;
        
        // Update main tab overlay
        const answerArea = document.getElementById('answer-area');
        if (answerArea) {
            answerArea.innerHTML = answerContent;
            answerArea.scrollTop = 0;
        }
        
        // Also update offscreen window if it exists
        if (this.offscreenWindow && !this.offscreenWindow.closed) {
            this.offscreenWindow.postMessage({
                type: 'ai-update-answer',
                content: answerContent
            }, '*');
        }

        console.log('✅ Answer displayed for question:', question);
    }

    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startSpeechRecognition();
        }
    }

    async startSpeechRecognition() {
        if (this.recognition) {
            try {
                this.isListening = true;
                this.recognition.start();
            } catch (error) {
                console.error('❌ Failed to start recognition:', error);
                this.updateStatus('❌ Failed to start listening');
            }
        }
    }

    stopListening() {
        if (this.recognition) {
            this.isListening = false;
            this.recognition.stop();
        }
    }

    testConnection() {
        this.processQuestion("Tell me about yourself");
    }

    async uploadResume() {
        const fileInput = document.getElementById('resume-file');
        const textInput = document.getElementById('resume-text');
        
        let resumeText = '';
        
        // Check if file is selected
        if (fileInput.files && fileInput.files[0]) {
            const file = fileInput.files[0];
            this.updateResumeStatus('⏳ Processing file...');
            
            try {
                resumeText = await this.extractTextFromFile(file);
                if (!resumeText.trim()) {
                    this.updateResumeStatus('❌ Could not extract text from file - try text input');
                    this.showTextInputHelper();
                    return;
                }
            } catch (error) {
                console.error('File processing error:', error);
                this.updateResumeStatus('❌ ' + error.message);
                this.showTextInputHelper();
                return;
            }
        } 
        // Check text input
        else if (textInput.value.trim()) {
            resumeText = textInput.value.trim();
        } 
        // No input provided
        else {
            this.updateResumeStatus('❌ Please select a file or enter text');
            return;
        }

        try {
            this.updateResumeStatus('⏳ Uploading resume...');
            
            const response = await fetch('http://localhost:8084/api/resume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    resume_text: resumeText
                })
            });

            if (response.ok) {
                const data = await response.json();
                const wordCount = Math.round(data.resume_length / 5); // Estimate words (avg 5 chars per word)
                this.updateResumeStatus(`🧠 Comprehensive resume memorized! (${data.resume_length} chars, ~${wordCount} words)`);
                
                // Clear inputs after successful upload
                fileInput.value = '';
                textInput.value = '';
                
                console.log(`✅ Large resume uploaded and memorized by AI: ${data.resume_length} characters`);
            } else {
                throw new Error(`Upload failed: ${response.status}`);
            }

        } catch (error) {
            console.error('❌ Resume upload failed:', error);
            this.updateResumeStatus('❌ Upload failed - Check AI service');
        }
    }

    async extractTextFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const arrayBuffer = e.target.result;
                
                if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
                    // Handle text files
                    const text = new TextDecoder().decode(arrayBuffer);
                    resolve(text);
                } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
                    // For PDF files, we'll need to suggest conversion
                    reject(new Error('PDF parsing requires conversion. Please copy your resume text and use the "📝 Text Input" option instead.'));
                } else if (file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || 
                          file.name.endsWith('.docx') || file.name.endsWith('.doc')) {
                    // For Word files, suggest conversion
                    reject(new Error('Word document parsing requires conversion. Please copy your resume text and use the "📝 Text Input" option instead.'));
                } else {
                    // Try to read as text anyway
                    try {
                        const text = new TextDecoder().decode(arrayBuffer);
                        if (text && text.trim().length > 50) {
                            resolve(text);
                        } else {
                            reject(new Error('Could not extract readable text. Please use the "📝 Text Input" option and paste your resume text.'));
                        }
                    } catch (error) {
                        reject(new Error('Unsupported file format. Please convert to TXT or use the "📝 Text Input" option.'));
                    }
                }
            };
            
            reader.onerror = () => reject(new Error('File reading failed'));
            
            // Read as ArrayBuffer to handle all file types
            reader.readAsArrayBuffer(file);
        });
    }

    handleFileSelection(event) {
        const file = event.target.files[0];
        if (file) {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
            this.updateResumeStatus(`📄 Selected: ${file.name} (${fileSizeMB}MB)`);
            
            // Show different messages for large files
            if (file.size > 1024 * 1024) { // > 1MB
                this.updateResumeStatus(`📄 Large resume detected: ${file.name} (${fileSizeMB}MB) - Ready to process`);
            }
            
            // Hide text input when file is selected
            document.getElementById('text-input-section').style.display = 'none';
        }
    }

    showTextInputHelper() {
        // Automatically show text input section when file processing fails
        const textSection = document.getElementById('text-input-section');
        const toggleBtn = document.getElementById('toggle-text-input');
        
        textSection.style.display = 'block';
        toggleBtn.textContent = '📁 File Upload';
        
        // Clear file input
        document.getElementById('resume-file').value = '';
        
        // Add helpful message
        setTimeout(() => {
            this.updateResumeStatus('💡 Please copy your resume text and paste it below');
        }, 2000);
    }

    toggleTextInput() {
        const textSection = document.getElementById('text-input-section');
        const toggleBtn = document.getElementById('toggle-text-input');
        
        if (textSection.style.display === 'none') {
            textSection.style.display = 'block';
            toggleBtn.textContent = '📁 File Upload';
            
            // Clear file input when switching to text
            document.getElementById('resume-file').value = '';
        } else {
            textSection.style.display = 'none';
            toggleBtn.textContent = '📝 Text Input';
        }
    }

    async clearResume() {
        try {
            this.updateResumeStatus('⏳ Clearing resume...');
            
            const response = await fetch('http://localhost:8084/api/resume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    resume_text: ''
                })
            });

            if (response.ok) {
                this.updateResumeStatus('Resume cleared from AI memory');
                
                // Clear all inputs
                document.getElementById('resume-file').value = '';
                document.getElementById('resume-text').value = '';
                
                console.log('✅ Resume cleared from AI memory');
            } else {
                throw new Error(`Clear failed: ${response.status}`);
            }

        } catch (error) {
            console.error('❌ Resume clear failed:', error);
            this.updateResumeStatus('❌ Clear failed');
        }
    }

    async checkResumeStatus() {
        try {
            const response = await fetch('http://localhost:8084/api/resume');
            if (response.ok) {
                const data = await response.json();
                if (data.has_resume) {
                    const wordCount = Math.round(data.resume_length / 5);
                    this.updateResumeStatus(`🧠 AI knows your background (${data.resume_length} chars, ~${wordCount} words)`);
                } else {
                    this.updateResumeStatus('Ready for your comprehensive resume');
                }
            }
        } catch (error) {
            console.log('Could not check resume status:', error);
            this.updateResumeStatus('Upload your 15-page resume for personalized responses');
        }
    }

    updateResumeStatus(message) {
        const statusElement = document.getElementById('resume-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateStatus(message) {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = message;
        }
        
        // Also update offscreen window if it exists
        if (this.offscreenWindow && !this.offscreenWindow.closed) {
            this.offscreenWindow.postMessage({
                type: 'ai-update-status',
                status: message
            }, '*');
        }
        
        console.log('📊 Status:', message);
    }

    toggleMinimize() {
        const overlay = this.overlay.querySelector('div');
        const minimizeBtn = document.getElementById('minimize-assistant');
        
        if (overlay.style.height === '40px') {
            // Restore
            overlay.style.height = 'auto';
            overlay.style.overflow = 'visible';
            minimizeBtn.textContent = '➖ Minimize';
            
            // Show all sections
            document.getElementById('resume-section').style.display = 'block';
            document.getElementById('answer-area').style.display = 'block';
            document.getElementById('toggle-listen').style.display = 'inline-block';
        } else {
            // Minimize
            overlay.style.height = '40px';
            overlay.style.overflow = 'hidden';
            minimizeBtn.textContent = '⬆️ Restore';
            
            // Hide sections except status
            document.getElementById('resume-section').style.display = 'none';
            document.getElementById('answer-area').style.display = 'none';
            document.getElementById('toggle-listen').style.display = 'none';
        }
    }
}

// Initialize when page loads
console.log('🚀 Starting AI Assistant initialization...');

function initializeAssistant() {
    try {
        if (window.location.hostname.includes('meet.google.com')) {
            console.log('✅ On Google Meet, creating assistant');
            const assistant = new AIInterviewAssistant();
            assistant.initialize();
            
            // Store reference for testing
            window.aiAssistant = assistant;
            console.log('✅ AI Assistant fully initialized and visible');
        } else {
            console.log('ℹ️ Not on Google Meet, skipping initialization');
        }
    } catch (error) {
        console.error('❌ Failed to initialize assistant:', error);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAssistant);
} else {
    initializeAssistant();
}

// Also expose for testing
window.testQuestion = function(question) {
    console.log('🧪 Testing question:', question);
    if (window.aiAssistant) {
        window.aiAssistant.processQuestion(question);
    } else {
        console.log('❌ Assistant not initialized yet');
    }
};

console.log('✅ AI Interview Assistant script loaded and ready');
