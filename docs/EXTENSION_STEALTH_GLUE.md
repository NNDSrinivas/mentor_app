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

## Mobile client

To view answers on a phone during stealth mode:

1. From the `mobile` directory run `npm start` (Expo) and open the app on your device.
2. Connect the device to the same network as the backend so it can reach `http://localhost:8081`.
3. When the extension detects a Chrome `desktopCapture` with the entire screen selected, the backend defaults the session's overlay channel to **mobile**, routing all answers to the phone.
