# Minimal Clients

This directory contains minimal client applications that fetch and display AI prompts from an authenticated API.

## React Native Client
- Fetches prompts from `API_URL` using a bearer `AUTH_TOKEN`.
- Displays the prompt in a simple full-screen view.
- Run tests: `npm test`

## Electron Client
- Desktop application that loads a prompt via the same authenticated API and displays it in a window.
- Run tests: `npm test`

Set environment variables `API_URL` and `AUTH_TOKEN` before running either client to target your service and authenticate.
