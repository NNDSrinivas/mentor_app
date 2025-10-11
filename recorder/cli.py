from __future__ import annotations

"""Command line interface for the recording service.

The CLI is intentionally lightweight: it does not perform real screen or
system audio capture. Instead it demonstrates how a front-end could
interact with :class:`backend.recording_service.RecordingService`. The
``start`` command creates an empty encrypted chunk to simulate the first
segment of a recording. ``stop`` currently only logs a message.
"""

import argparse
import os
from backend.recording_service import RecordingService


def _simulate_chunk() -> bytes:
    """Return placeholder bytes representing a 20s media chunk."""
    return b"\x00" * 10  # trivial stand-in for encoded media


def start_recording(meeting_id: str) -> None:
    service = RecordingService()
    service.save_chunk(meeting_id, _simulate_chunk(), 0)
    print(f"recording started for {meeting_id}")


def stop_recording(meeting_id: str) -> None:
    print(f"recording stopped for {meeting_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recorder")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="begin recording")
    p_start.add_argument("--meetingId", required=True, dest="meeting_id")
    p_start.add_argument("--window")
    p_start.add_argument("--display", type=int)

    p_stop = sub.add_parser("stop", help="stop recording")
    p_stop.add_argument("--meetingId", required=True, dest="meeting_id")

    args = parser.parse_args(argv)

    if args.command == "start":
        start_recording(args.meeting_id)
    elif args.command == "stop":
        stop_recording(args.meeting_id)

    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
