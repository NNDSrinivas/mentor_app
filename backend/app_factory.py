from __future__ import annotations
from flask import Flask, jsonify, request
from .healthz import bp as healthz_bp
from .meeting_events import MeetingEventRouter
from .middleware import rate_limit, record_cost


def create_app():
    """Application factory for tests and development."""
    app = Flask(__name__)
    # Register health check blueprint
    app.register_blueprint(healthz_bp)

    router = MeetingEventRouter()

    @app.post("/api/meeting-events")
    @rate_limit("meeting")
    def meeting_events():
        payload = request.get_json(silent=True) or {}
        # track token usage; default to 0 if not provided
        tokens = int(payload.get("tokens", 0)) if isinstance(payload.get("tokens"), int) else 0
        record_cost(tokens=tokens)
        try:
            result = router.handle_event(payload)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "result": result})

    return app
