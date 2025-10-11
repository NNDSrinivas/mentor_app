window.addEventListener('DOMContentLoaded', async () => {
  const promptEl = document.getElementById('prompt');
  const prompt = await window.api.fetchPrompt();
  promptEl.textContent = prompt;
});
