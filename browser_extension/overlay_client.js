// Lightweight client to consume SSE answers and render a private overlay.
// Include from your content.js after detecting meeting + meetingId.

(function() {
  if (window.__aim_overlay_installed__) return;
  window.__aim_overlay_installed__ = true;

  const state = { meetingId: null, source: null, backend: 'http://localhost:8080' };

  function ensureOverlay() {
    let el = document.getElementById('aim-overlay');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'aim-overlay';
    el.style.cssText = [
      'position: fixed','top: 10px','right: 10px','width: 520px','max-height: 80vh',
      'overflow:auto','z-index:2147483647','background: rgba(0,0,0,0.96)','color:#0f0',
      'font: 12px/1.4 monospace','border:1px solid #0f0','border-radius:12px','padding:10px',
      'opacity:0.95'
    ].join(';');
    document.body.appendChild(el);
    return el;
  }

  function connect(meetingId) {
    state.meetingId = meetingId;
    try { if (state.source) state.source.close(); } catch(e) {}
    const url = state.backend + '/api/answer-stream/' + encodeURIComponent(meetingId);
    const es = new EventSource(url);
    state.source = es;
    const el = ensureOverlay();
    el.innerHTML = '<b>AI Mentor</b><div id="aim-answers"></div>';
    const out = el.querySelector('#aim-answers');
    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'answer') {
          const d = document.createElement('div');
          d.style.margin = '8px 0';
          d.textContent = msg.text;
          out.appendChild(d);
          out.scrollTop = out.scrollHeight;
        }
      } catch(e) {/* ignore */}
    };
    es.onerror = () => {
      setTimeout(() => connect(meetingId), 3000);
    };
  }

  window.AIMOverlay = { connect, setBackend: (b) => state.backend = b };
  console.log('AIM overlay client ready');
})();
