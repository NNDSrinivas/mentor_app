#!/usr/bin/env python3
"""Universal IDE Bridge

This module exposes HTTP endpoints that act as a bridge between IDE
integrations (like the VS Code ExtensionBridge) and the backend AI
services.  It relays questions, code generation requests and task
updates while also providing a lightweight message queue so different
extensions can communicate through the service.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, List

from flask import Flask, jsonify, request
from flask_cors import CORS

# Lazy imports for heavy services
_ai_assistant = None
_memory_service = None


def get_ai_assistant():
    """Instantiate and cache the :class:`AIAssistant` lazily."""
    global _ai_assistant
    if _ai_assistant is None:
        from app.ai_assistant import AIAssistant

        _ai_assistant = AIAssistant()
    return _ai_assistant


def get_memory_service():
    """Instantiate and cache the :class:`MemoryService` lazily."""
    global _memory_service
    if _memory_service is None:
        from backend.memory_service import MemoryService

        _memory_service = MemoryService()
    return _memory_service


log = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Simple in-memory message queues used by the extension bridge
# ---------------------------------------------------------------------------
_vscode_messages: List[Dict[str, Any]] = []
_browser_messages: List[Dict[str, Any]] = []
_current_context: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# AI service endpoints
# ---------------------------------------------------------------------------
@app.route("/api/ask", methods=["POST"])
def ask_question():
    """Handle general question-answering requests from IDEs."""
    data = request.get_json(force=True) or {}
    question: str | None = data.get("question")
    context: Dict[str, Any] = data.get("context", {})

    if not question:
        return jsonify({"error": "Question is required"}), 400

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        ai = get_ai_assistant()
        answer = loop.run_until_complete(ai._generate_ai_response(question, context))
    finally:
        loop.close()

    return jsonify({
        "response": answer,
        "timestamp": datetime.now().isoformat(),
        "context": context,
    })


@app.route("/api/generate-code", methods=["POST"])
def generate_code():
    """Generate code based on a prompt."""
    data = request.get_json(force=True) or {}
    prompt: str | None = data.get("prompt")
    context: Dict[str, Any] = data.get("context", {})

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    question = f"Write code for the following request:\n{prompt}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        ai = get_ai_assistant()
        code = loop.run_until_complete(ai._generate_ai_response(question, context))
    finally:
        loop.close()

    return jsonify({
        "code": code,
        "timestamp": datetime.now().isoformat(),
        "context": context,
    })


@app.route("/api/task/update", methods=["POST"])
def update_task():
    """Store or update task information in persistent memory."""
    data = request.get_json(force=True) or {}
    task_id: str | None = data.get("task_id")
    description: str | None = data.get("description")
    metadata: Dict[str, Any] = data.get("metadata", {})

    if not task_id or not description:
        return jsonify({"error": "task_id and description required"}), 400

    mem = get_memory_service()
    mem.add_task(task_id, description, metadata=metadata)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Message relay endpoints
# ---------------------------------------------------------------------------
@app.route("/api/vscode-message", methods=["POST"])
def queue_for_vscode():
    """Queue a message destined for the VS Code extension."""
    message = request.get_json(force=True) or {}
    message.setdefault("timestamp", datetime.now().isoformat())
    _vscode_messages.append(message)
    return jsonify({"queued": True})


@app.route("/api/vscode-messages", methods=["GET"])
def fetch_vscode_messages():
    """Retrieve and clear messages for the VS Code extension."""
    messages = list(_vscode_messages)
    _vscode_messages.clear()
    return jsonify({"messages": messages})


@app.route("/api/browser-message", methods=["POST"])
def queue_for_browser():
    """Queue a message destined for the browser extension."""
    message = request.get_json(force=True) or {}
    message.setdefault("timestamp", datetime.now().isoformat())
    _browser_messages.append(message)
    return jsonify({"queued": True})


@app.route("/api/browser-messages", methods=["GET"])
def fetch_browser_messages():
    """Retrieve and clear messages for the browser extension."""
    messages = list(_browser_messages)
    _browser_messages.clear()
    return jsonify({"messages": messages})


@app.route("/api/sync-context", methods=["POST"])
def sync_context():
    """Synchronize meeting/coding context from extensions."""
    data = request.get_json(force=True) or {}
    _current_context.update(data)
    return jsonify({"status": "synced"})


@app.route("/api/bridge-sync", methods=["POST"])
def bridge_sync():
    """Generic endpoint to store bridge events.

    Currently it simply records the events in the in-memory context store so
    other components can inspect them if needed.
    """
    data = request.get_json(force=True) or {}
    events: List[Dict[str, Any]] = _current_context.setdefault("events", [])
    events.append(data)
    return jsonify({"status": "received"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=8080)
