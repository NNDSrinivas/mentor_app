// inject.js - Simple injection script for AI Mentor Assistant
console.log('🚀 AI Mentor inject.js loaded');

// Initialize AI Mentor when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAIMentor);
} else {
    initAIMentor();
}

function initAIMentor() {
    console.log('🤖 AI Mentor - Initializing injection');
    
    // Signal that AI Mentor is active
    window.AIMentorActive = true;
    
    // Dispatch custom event to notify content scripts
    const event = new CustomEvent('AIMentorReady', {
        detail: { platform: detectPlatform() }
    });
    document.dispatchEvent(event);
}

function detectPlatform() {
    const hostname = window.location.hostname;
    if (hostname.includes('zoom.us')) return 'zoom';
    if (hostname.includes('teams.microsoft.com')) return 'teams';
    if (hostname.includes('meet.google.com')) return 'google-meet';
    if (hostname.includes('webex.com')) return 'webex';
    return 'unknown';
}
