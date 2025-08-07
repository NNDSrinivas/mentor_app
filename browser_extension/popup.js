// Allow user to configure backend URL for local dev / production
document.addEventListener('DOMContentLoaded', async () => {
  const input = document.getElementById('backendUrl');
  const status = document.getElementById('status');
  const saved = await chrome.storage.local.get(['backendUrl']);
  input.value = saved.backendUrl || 'http://localhost:8080';
  document.getElementById('save').addEventListener('click', async () => {
    await chrome.storage.local.set({ backendUrl: input.value.trim() });
    status.textContent = 'Saved';
    setTimeout(() => status.textContent = '', 1500);
  });
});
