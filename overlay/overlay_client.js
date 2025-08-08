// overlay/overlay_client.js

class SmartOverlayClient {
    constructor() {
        this.sessionId = null;
        this.eventSource = null;
        this.answers = [];
        this.isVisible = false;
        this.currentIndex = 0;
        this.readBackDetection = new ReadBackDetection();
        this.setup();
    }

    setup() {
        this.createOverlayElements();
        this.bindEvents();
        this.startSession();
        
        // Auto-hide/show based on screen sharing detection
        this.detectScreenSharing();
    }

    createOverlayElements() {
        // Create main overlay container
        this.overlay = document.createElement('div');
        this.overlay.id = 'ai-mentor-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 350px;
            max-height: 80vh;
            background: rgba(0, 0, 0, 0.95);
            border: 1px solid #333;
            border-radius: 12px;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            z-index: 999999;
            backdrop-filter: blur(10px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            display: none;
            overflow: hidden;
        `;

        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 12px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        header.innerHTML = `
            <span style="font-weight: 600;">AI Interview Assistant</span>
            <div>
                <button id="overlay-minimize" style="background: none; border: none; color: white; cursor: pointer; margin-right: 8px;">─</button>
                <button id="overlay-close" style="background: none; border: none; color: white; cursor: pointer;">✕</button>
            </div>
        `;

        // Content area
        this.content = document.createElement('div');
        this.content.style.cssText = `
            padding: 16px;
            max-height: 60vh;
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: #666 #333;
        `;

        // Answer display
        this.answerDisplay = document.createElement('div');
        this.answerDisplay.style.cssText = `
            margin-bottom: 16px;
            line-height: 1.5;
            background: #1a1a1a;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        `;

        // Navigation controls
        const nav = document.createElement('div');
        nav.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #333;
        `;
        nav.innerHTML = `
            <button id="prev-answer" style="background: #333; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;">‹ Prev</button>
            <span id="answer-counter" style="color: #999; font-size: 12px;">0 / 0</span>
            <button id="next-answer" style="background: #333; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;">Next ›</button>
        `;

        // Status indicator
        this.statusIndicator = document.createElement('div');
        this.statusIndicator.style.cssText = `
            padding: 8px 16px;
            background: #2a2a2a;
            font-size: 12px;
            color: #999;
            border-top: 1px solid #333;
        `;
        this.statusIndicator.textContent = 'Connecting...';

        // Assemble overlay
        this.overlay.appendChild(header);
        this.content.appendChild(this.answerDisplay);
        this.content.appendChild(nav);
        this.overlay.appendChild(this.content);
        this.overlay.appendChild(this.statusIndicator);
        
        document.body.appendChild(this.overlay);
    }

    bindEvents() {
        // Header controls
        document.getElementById('overlay-minimize').onclick = () => this.minimize();
        document.getElementById('overlay-close').onclick = () => this.hide();

        // Navigation
        document.getElementById('prev-answer').onclick = () => this.showPreviousAnswer();
        document.getElementById('next-answer').onclick = () => this.showNextAnswer();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'a') {
                e.preventDefault();
                this.toggle();
            }
            if (this.isVisible) {
                if (e.key === 'ArrowLeft') this.showPreviousAnswer();
                if (e.key === 'ArrowRight') this.showNextAnswer();
                if (e.key === 'Escape') this.hide();
            }
        });

        // Auto-scroll detection
        this.content.addEventListener('scroll', () => {
            this.readBackDetection.onScroll();
        });
    }

    async startSession() {
        try {
            // Create new session
            const response = await fetch('http://localhost:8080/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_level: this.getUserLevel(),
                    meeting_type: 'technical_interview',
                    user_name: 'overlay_user'
                })
            });

            if (!response.ok) throw new Error('Failed to create session');
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            this.connectToEventStream();
            this.updateStatus('Connected', 'success');
            
        } catch (error) {
            console.error('Failed to start session:', error);
            this.updateStatus('Connection failed', 'error');
        }
    }

    connectToEventStream() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(`http://localhost:8080/api/sessions/${this.sessionId}/stream`);
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (error) {
                console.error('Error parsing event data:', error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.updateStatus('Disconnected', 'error');
            
            // Reconnect after delay
            setTimeout(() => {
                if (this.sessionId) {
                    this.connectToEventStream();
                }
            }, 5000);
        };
    }

    handleEvent(data) {
        switch (data.type) {
            case 'new_answer':
                this.addAnswer(data.data);
                break;
            case 'historical_answer':
                this.addAnswer(data.data, false);
                break;
            case 'session_ended':
                this.updateStatus('Session ended', 'warning');
                break;
            case 'keepalive':
                // Keep connection alive
                break;
            case 'build_status':
                this.showBuildStatus(data.data);
                break;
        }
    }

    addAnswer(answerData, isNew = true) {
        this.answers.push(answerData);
        
        if (isNew) {
            this.currentIndex = this.answers.length - 1;
            this.displayCurrentAnswer();
            this.show();
            
            // Auto-scroll if user is reading
            if (this.readBackDetection.isUserReading()) {
                this.autoScrollToNewAnswer();
            }
            
            this.updateStatus(`${this.answers.length} answers available`, 'success');
        } else {
            // Historical answer, just update counter
            this.updateAnswerCounter();
        }
    }

    showBuildStatus(info) {
        const color = info.status === 'success' ? '#4caf50' : '#ff5555';
        const msg = `Build ${info.status} for PR #${info.pr_number}: ${info.title || ''}`;
        this.answerDisplay.innerHTML = `<div style="color:${color};">${this.escapeHtml(msg)}</div>`;
        this.show();
        this.updateStatus(`Build ${info.status}`, info.status === 'success' ? 'success' : 'error');
    }

    displayCurrentAnswer() {
        if (this.answers.length === 0) {
            this.answerDisplay.innerHTML = '<p style="color: #666; font-style: italic;">No answers yet. Waiting for questions...</p>';
            return;
        }

        const answer = this.answers[this.currentIndex];
        
        this.answerDisplay.innerHTML = `
            <div style="margin-bottom: 12px;">
                <div style="color: #667eea; font-weight: 600; font-size: 13px; margin-bottom: 8px;">
                    QUESTION:
                </div>
                <div style="color: #ccc; margin-bottom: 12px; font-size: 13px; line-height: 1.4;">
                    ${this.escapeHtml(answer.question)}
                </div>
                <div style="color: #667eea; font-weight: 600; font-size: 13px; margin-bottom: 8px;">
                    SUGGESTED ANSWER (${answer.user_level}):
                </div>
                <div style="line-height: 1.6;">
                    ${this.formatAnswer(answer.answer)}
                </div>
            </div>
            <div style="color: #666; font-size: 11px; margin-top: 12px;">
                ${new Date(answer.timestamp).toLocaleTimeString()}
                ${answer.memory_context_used ? ' • Context-aware' : ''}
            </div>
        `;

        this.updateAnswerCounter();
    }

    formatAnswer(answer) {
        // Format the answer with better readability
        return this.escapeHtml(answer)
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code style="background: #333; padding: 2px 4px; border-radius: 3px;">$1</code>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateAnswerCounter() {
        const counter = document.getElementById('answer-counter');
        if (counter) {
            counter.textContent = `${this.currentIndex + 1} / ${this.answers.length}`;
        }
    }

    showPreviousAnswer() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.displayCurrentAnswer();
        }
    }

    showNextAnswer() {
        if (this.currentIndex < this.answers.length - 1) {
            this.currentIndex++;
            this.displayCurrentAnswer();
        }
    }

    autoScrollToNewAnswer() {
        // Smooth scroll to top to show new answer
        this.content.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    show() {
        this.overlay.style.display = 'block';
        this.isVisible = true;
    }

    hide() {
        this.overlay.style.display = 'none';
        this.isVisible = false;
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }

    minimize() {
        if (this.content.style.display === 'none') {
            this.content.style.display = 'block';
        } else {
            this.content.style.display = 'none';
        }
    }

    updateStatus(message, type = 'info') {
        const colors = {
            info: '#667eea',
            success: '#4ade80',
            warning: '#fbbf24',
            error: '#ef4444'
        };
        
        this.statusIndicator.style.color = colors[type];
        this.statusIndicator.textContent = message;
    }

    getUserLevel() {
        // Try to detect user level from URL, localStorage, or default
        return localStorage.getItem('user_level') || 
               new URLSearchParams(window.location.search).get('level') || 
               'IC5';
    }

    detectScreenSharing() {
        // Hide overlay during screen sharing to maintain privacy
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            // This is a simplified detection - in reality you'd need more sophisticated logic
            setInterval(() => {
                // Check if user is likely in a video call
                const isInCall = document.querySelector('[data-is-screen-sharing="true"]') || 
                               window.location.href.includes('meet.google.com') ||
                               window.location.href.includes('zoom.us');
                
                if (isInCall && this.isVisible) {
                    this.hide();
                    console.log('Auto-hiding overlay for screen sharing');
                }
            }, 5000);
        }
    }
}

class ReadBackDetection {
    constructor() {
        this.scrollEvents = [];
        this.readingThreshold = 2000; // 2 seconds of no scrolling indicates reading
    }

    onScroll() {
        this.scrollEvents.push(Date.now());
        
        // Keep only recent events
        const cutoff = Date.now() - 10000; // 10 seconds
        this.scrollEvents = this.scrollEvents.filter(time => time > cutoff);
    }

    isUserReading() {
        if (this.scrollEvents.length === 0) return false;
        
        const lastScroll = this.scrollEvents[this.scrollEvents.length - 1];
        const timeSinceLastScroll = Date.now() - lastScroll;
        
        return timeSinceLastScroll > this.readingThreshold;
    }
}

// Auto-start the overlay when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new SmartOverlayClient();
    });
} else {
    new SmartOverlayClient();
}

// Export for manual instantiation if needed
window.SmartOverlayClient = SmartOverlayClient;
