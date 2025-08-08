const { contextBridge } = require('electron');

const API_URL = process.env.API_URL || 'http://localhost:8000/api/prompts';
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';

async function fetchPrompt() {
  try {
    const res = await fetch(API_URL, {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
      },
    });
    const data = await res.json();
    return data.prompt || 'No prompt';
  } catch (err) {
    return 'Failed to fetch prompt';
  }
}

contextBridge.exposeInMainWorld('api', {
  fetchPrompt,
});
