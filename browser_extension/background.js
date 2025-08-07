// Background script for AI Mentor Assistant (updated for configurable backend + offscreen audio)
console.log('🚀 AI Mentor Background Script Loading (v1.8.0)...');

const DEFAULT_BACKEND = 'http://localhost:8080';

async function getBackendUrl() {
  const res = await chrome.storage.local.get(['backendUrl']);
  return res.backendUrl || DEFAULT_BACKEND;
}

// Ensure Offscreen document exists (for audio processing without visible UI)
async function ensureOffscreenDocument() {
  const existing = await chrome.offscreen.hasDocument?.().catch(() => false);
  if (existing) return;
  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['AUDIO_PLAYBACK', 'AUDIO_WORKLET'],
      justification: 'Audio processing for meeting transcription and VAD'
    });
    console.log('🎤 Offscreen document created');
  } catch (e) {
    console.warn('Offscreen create failed (might already exist):', e.message);
  }
}

class MeetingDetector {
  constructor() {
    this.isRecording = false;
    this.currentMeeting = null;

    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === 'complete') {
        this.checkForMeeting(tab);
      }
    });

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      this.handleMessage(message, sender, sendResponse);
    });
  }

  checkForMeeting(tab) {
    const meetingPatterns = [
      /meet\.google\.com\/[a-z0-9-]+/,
      /teams\.microsoft\.com.*meetup-join/,
      /.*\.zoom\.us\/j\/\d+/,
      /zoom\.us\/j\/\d+/
    ];
    const isMeetingUrl = meetingPatterns.some(p => p.test(tab.url || ''));
    if (isMeetingUrl && !this.isRecording) {
      this.startMeetingDetection(tab);
    }
  }

  async startMeetingDetection(tab) {
    console.log('🎤 Meeting detected');
    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
      const backend = await getBackendUrl();
      this.notifyBackend(backend, 'meeting_detected', { url: tab.url, title: tab.title, timestamp: Date.now() });
    } catch (e) {
      console.error('Failed to inject content script:', e);
    }
  }

  async handleMessage(message, sender, sendResponse) {
    const backend = await getBackendUrl();
    switch (message.type) {
      case 'meeting_started':
        this.isRecording = true;
        this.currentMeeting = {
          id: 'meeting_' + Date.now() + '_' + Math.random().toString(36).slice(2),
          startTime: Date.now(),
          platform: this.detectPlatform(message.data.url || sender?.tab?.url || ''),
          ...message.data
        };
        await ensureOffscreenDocument();
        this.notifyBackend(backend, 'start_recording', this.currentMeeting);
        chrome.action.setBadgeText({ text: 'REC' });
        chrome.action.setBadgeBackgroundColor({ color: '#ff4444' });
        break;

      case 'meeting_ended':
        this.isRecording = false;
        if (this.currentMeeting) {
          this.currentMeeting.endTime = Date.now();
          this.currentMeeting.duration = this.currentMeeting.endTime - this.currentMeeting.startTime;
          this.notifyBackend(backend, 'stop_recording', this.currentMeeting);
          this.currentMeeting = null;
        }
        chrome.action.setBadgeText({ text: '' });
        break;

      case 'participant_speaking':
      case 'screen_shared':
      case 'caption_chunk':
        this.notifyBackend(backend, message.type, { meetingId: this.currentMeeting?.id, ...message.data, ts: Date.now() });
        break;
    }
  }

  async notifyBackend(backend, action, data) {
    try {
      const res = await fetch(backend + '/api/meeting-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, data, timestamp: Date.now() })
      });
      if (!res.ok) console.warn('Backend notification failed:', res.status);
    } catch (e) {
      console.warn('Backend not available:', e.message);
    }
  }

  detectPlatform(url) {
    if (url.includes('meet.google.com')) return 'google_meet';
    if (url.includes('teams.microsoft.com')) return 'microsoft_teams';
    if (url.includes('zoom.us')) return 'zoom';
    return 'unknown';
  }
}

new MeetingDetector();

// Simple options UI saving
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['backendUrl'], (res) => {
    if (!res.backendUrl) chrome.storage.local.set({ backendUrl: DEFAULT_BACKEND });
  });
});
