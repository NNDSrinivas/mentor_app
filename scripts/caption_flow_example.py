"""Demo script for streaming captions from sample meetings.

Each meeting platform client reads lines from a sample file and sends them
through the RealtimeSessionManager.
"""
from __future__ import annotations

import pprint

import os
import sys

# Ensure project root is on the path when executed directly
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.capture import ZoomClient, TeamsClient, GoogleMeetClient
from app.realtime import get_session_manager

SAMPLES = {
    ZoomClient: "docs/sample_meetings/zoom.txt",
    TeamsClient: "docs/sample_meetings/teams.txt",
    GoogleMeetClient: "docs/sample_meetings/google_meet.txt",
}


def run_demo():
    manager = get_session_manager()
    for client_cls, sample in SAMPLES.items():
        session_id = manager.create_session({"user_name": client_cls.__name__})
        client = client_cls(session_id=session_id, caption_file=sample)
        client.stream_captions(delay=0.01)
        session = manager.get_session(session_id)
        print(f"\n{client_cls.__name__} captured:")
        pprint.pp(session.caption_buffer if session else [])
        manager.end_session(session_id)


if __name__ == "__main__":
    run_demo()
