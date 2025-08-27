const { test, expect } = require('@playwright/test');
const path = require('path');

test('relay POST fires when presenting is detected', async ({ page }) => {
  let relayCalled = false;
  await page.route('http://localhost:8081/api/relay/mobile', route => {
    relayCalled = true;
    route.fulfill({ status: 200, body: 'ok' });
  });

  await page.setContent('<div id="status"></div>');

  await page.evaluate(() => {
    window.STEALTH_ON = false;
    window.chrome = {
      runtime: {
        sendMessage: (msg) => {
          if (msg.type === 'aim_stealth_mode') {
            window.STEALTH_ON = !!(msg.data && msg.data.on);
          } else if (msg.type === 'aim_answer' && window.STEALTH_ON) {
            fetch('http://localhost:8081/api/relay/mobile', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(msg.data || {})
            });
          }
        }
      }
    };
  });

  const contentPath = path.resolve('browser_extension/content.js');
  await page.addScriptTag({ path: contentPath });

  await page.evaluate(() => {
    document.body.innerHTML = 'You are presenting';
  });

  await page.waitForTimeout(2000);

  await page.evaluate(() => {
    window.chrome.runtime.sendMessage({ type: 'aim_answer', data: { meetingId: 'm1', text: 'hello' } });
  });

  await page.waitForTimeout(500);
  expect(relayCalled).toBeTruthy();
});
