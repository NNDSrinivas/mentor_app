let STEALTH_ON = false;

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'aim_stealth_mode') {
    STEALTH_ON = !!(message.data && message.data.on);
  } else if (message.type === 'aim_answer' && STEALTH_ON) {
    fetch('http://localhost:8081/api/relay/mobile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meetingId: message.data && message.data.meetingId,
        text: message.data && message.data.text
      })
    }).catch(err => console.warn('relay failed', err));
  }
});
