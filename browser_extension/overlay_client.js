// overlay_client.js — Wave 7
(() => {
  if (window.__aim_overlay_installed__) return;
  window.__aim_overlay_installed__ = true;

  const state = {
    meetingId: null,
    source: null,
    backend: 'http://localhost:8080',
    wsApprovals: 'ws://localhost:8001',
    currentAnswer: '',
    scrollIndex: 0,
    stealth: false,   // when true -> do not render overlay text in-page (route to mobile)
    readingMode: true // auto-scroll when we detect user's speech matches answer
  };

  // --- UI
  function ensureOverlay() {
    let el = document.getElementById('aim-overlay');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'aim-overlay';
    el.style.cssText = [
      'position:fixed','top:10px','right:10px','width:520px','max-height:80vh',
      'overflow:auto','z-index:2147483647','background:rgba(0,0,0,0.96)','color:#0f0',
      'font:12px/1.5 monospace','border:1px solid #0f0','border-radius:12px','padding:10px','opacity:0.95'
    ].join(';');
    const head = document.createElement('div');
    head.style.cssText = 'display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:6px';
    head.innerHTML = `
      <b>AI Mentor</b>
      <span id="aim-stealth" style="cursor:pointer;border:1px solid #0f0;border-radius:8px;padding:2px 6px;">Stealth: Off</span>
      <span id="aim-reading" style="cursor:pointer;border:1px solid #0f0;border-radius:8px;padding:2px 6px;">AutoScroll: On</span>
    `;
    const out = document.createElement('div');
    out.id = 'aim-answers';
    el.appendChild(head); el.appendChild(out);
    document.body.appendChild(el);

    head.querySelector('#aim-stealth').onclick = () => {
      state.stealth = !state.stealth;
      head.querySelector('#aim-stealth').textContent = `Stealth: ${state.stealth ? 'On':'Off'}`;
      document.getElementById('aim-answers').style.display = state.stealth ? 'none' : 'block';
      // Also tell background to route answers to mobile if stealth on
      chrome.runtime?.sendMessage?.({type:'aim_stealth_mode', data:{on: state.stealth}});
    };
    head.querySelector('#aim-reading').onclick = () => {
      state.readingMode = !state.readingMode;
      head.querySelector('#aim-reading').textContent = `AutoScroll: ${state.readingMode ? 'On':'Off'}`;
    };
    return el;
  }

  // --- SSE answers
  function connect(meetingId) {
    state.meetingId = meetingId;
    try { state.source?.close(); } catch {}
    const url = `${state.backend}/api/answer-stream/${encodeURIComponent(meetingId)}`;
    const es = new EventSource(url);
    state.source = es;
    const el = ensureOverlay();
    const out = el.querySelector('#aim-answers');
    out.innerHTML = '';

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'answer') {
          state.currentAnswer = msg.text;
          state.scrollIndex = 0;
          if (!state.stealth) {
            const d = document.createElement('div');
            d.className = 'aim-answer';
            d.style.margin = '8px 0';
            d.textContent = msg.text;
            out.appendChild(d);
            out.scrollTop = out.scrollHeight;
          }
          // Always broadcast to background (mobile relay)
          chrome.runtime?.sendMessage?.({type:'aim_answer', data:{meetingId, text: msg.text}});
        }
      } catch {}
    };
    es.onerror = () => setTimeout(() => connect(meetingId), 2000);
  }

  // --- Mic alignment (read-back auto-scroll)
  // Strategy: browser SpeechRecognition if available; fallback to noop.
  function startReadBackAlignment() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn('SpeechRecognition not available; skipping read-back alignment');
      return;
    }
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (ev) => {
      if (!state.readingMode || state.stealth) return;
      const r = ev.results[ev.results.length - 1];
      const transcript = (r[0]?.transcript || '').trim();
      if (!transcript || state.currentAnswer.length === 0) return;
      // Fuzzy match: find the latest index of transcript in currentAnswer
      const idx = state.currentAnswer.toLowerCase().indexOf(transcript.toLowerCase(), state.scrollIndex);
      if (idx >= 0) {
        state.scrollIndex = idx + transcript.length;
        const out = document.getElementById('aim-answers');
        if (out) out.scrollTop = out.scrollHeight * (state.scrollIndex / (state.currentAnswer.length + 1));
      }
    };
    rec.onerror = () => { try { rec.stop(); } catch {} ; setTimeout(startReadBackAlignment, 1500); };
    try { rec.start(); } catch {}
  }

  // --- Detect screen sharing in-page (Meet/Teams/Zoom heuristics)
  function monitorScreenShare() {
    const detect = () => {
      const txt = document.body.innerText || '';
      const hints = ['You are presenting', 'You\'re presenting', 'Stop presenting', 'Stop sharing', 'You are sharing'];
      const yes = hints.some(h => txt.includes(h));
      if (yes && !state.stealth) {
        // Flip to stealth automatically
        state.stealth = true;
        const hdr = document.querySelector('#aim-stealth');
        if (hdr) hdr.textContent = 'Stealth: On';
        const out = document.getElementById('aim-answers');
        if (out) out.style.display = 'none';
        chrome.runtime?.sendMessage?.({type:'aim_stealth_mode', data:{on:true}});
      }
    };
    setInterval(detect, 1500);
  }

  window.AIMOverlay = {
    connect,
    setBackend: (b) => state.backend = b
  };

  ensureOverlay();
  startReadBackAlignment();
  monitorScreenShare();
  console.log('AIM overlay v7 ready');
})();
