# Extension glue for auto-stealth → mobile relay

In `browser_extension/background.js` add:

```javascript
let STEALTH_ON = false;

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'aim_stealth_mode') {
    STEALTH_ON = !!message.data?.on;
  }
  if (message.type === 'aim_answer' && STEALTH_ON) {
    fetch('http://localhost:8081/api/relay/mobile', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ type:'answer', text: message.data.text, meetingId: message.data.meetingId })
    }).catch(()=>{});
  }
});
```

## Full display sharing fallback

The extension now detects when the user shares their *entire display* using
`navigator.mediaDevices.getDisplayMedia`.  When this happens the in-page
overlay is suppressed to avoid leaking answers into the meeting stream.

* If an Electron helper is running locally, answers are relayed to it via
  `http://localhost:8081/api/relay/electron` and shown in an always-on-top
  click-through window.  Use **Ctrl+Shift+O** to toggle the helper's
  visibility.
* If the helper is unavailable the extension falls back to the mobile relay
  endpoint described above.

For privacy, users should prefer sharing a single window or tab instead of the
entire display.  Full-display sharing will always trigger the helper/mobile
fallback behavior.
