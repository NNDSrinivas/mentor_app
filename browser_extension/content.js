const INDICATORS = [
  'You are presenting',
  'Stop sharing',
  'You are sharing',
  'Stop presenting'
];

let lastState = null;

function checkSharing() {
  const text = document.body ? document.body.innerText : '';
  const on = INDICATORS.some(ind => text.includes(ind));
  if (on !== lastState) {
    lastState = on;
    chrome.runtime.sendMessage({
      type: 'aim_stealth_mode',
      data: { on }
    });
  }
}

setInterval(checkSharing, 1500);
checkSharing();
