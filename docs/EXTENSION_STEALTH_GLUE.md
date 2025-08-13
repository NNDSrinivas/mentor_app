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
