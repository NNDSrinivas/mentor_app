"""Main entry point for the AI Mentor Assistant prototype.

This script demonstrates how the different modules in the application
could be orchestrated.  It captures a meeting, transcribes it, summarizes
the transcript, records the screen and analyzes the screen video.  All
functions currently return placeholder data.
"""
import logging
from . import capture, transcription, summarization, screen_record, knowledge_base


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_demo() -> None:
    meeting_id = "demo_meeting"

    # Capture meeting (audio/video)
    audio_path, video_path = capture.capture_meeting(meeting_id)

    # Transcribe audio
    transcript = transcription.transcribe_audio(audio_path)

    # Summarize transcript
    summary = summarization.summarize_transcript(transcript)
    print("\nGenerated summary:\n", summary)

    # Record screen
    screen_video_path = screen_record.record_screen(meeting_id)

    # Analyze screen video
    analysis_results = screen_record.analyze_screen_video(screen_video_path)
    print("\nScreen analysis results:\n", analysis_results)

    # Demonstrate knowledge base ingestion and query
    knowledge_base.ingest_documents(["Sample code documentation", "Architecture overview"])
    kb_results = knowledge_base.query_knowledge_base("What is the architecture of service X?")
    print("\nKnowledge base query results:\n", kb_results)

    # Ask a question about the meeting
    answer = summarization.answer_question(
        "What was the main decision made in the meeting?", transcript["text"]
    )
    print("\nAnswer to question:\n", answer)


if __name__ == "__main__":
    configure_logging()
    run_demo()