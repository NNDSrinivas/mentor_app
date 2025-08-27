// overlay/reader.js
// Simple read‑back alignment helper used by the browser overlay.

class ReadBackAligner {
  constructor(answer) {
    this.answer = answer || '';
    this.cursor = 0;
  }

  update(spoken, windowSize = 10) {
    const words = spoken.trim().split(/\s+/);
    if (!words.length) return this.cursor;
    const segment = words.slice(-windowSize).join(' ').toLowerCase();
    const answerLower = this.answer.toLowerCase();
    let idx = answerLower.indexOf(segment);
    if (idx !== -1) {
      this.cursor = idx + segment.length;
      return this.cursor;
    }
    // fuzzy match via longest substring
    let best = { a: 0, len: 0 };
    for (let i = 0; i < answerLower.length; i++) {
      for (let j = i; j < answerLower.length; j++) {
        const sub = answerLower.slice(i, j + 1);
        if (segment.includes(sub) && sub.length > best.len) {
          best = { a: i, len: sub.length };
        }
      }
    }
    this.cursor = best.a + best.len;
    return this.cursor;
  }

  scroll(container) {
    if (!container) return;
    const ratio = this.cursor / this.answer.length;
    const target = ratio * (container.scrollHeight - container.clientHeight);
    container.scrollTo({ top: target, behavior: 'smooth' });
  }
}

window.ReadBackAligner = ReadBackAligner;
