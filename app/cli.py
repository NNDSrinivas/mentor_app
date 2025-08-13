"""Command-line interface for the AI Mentor Assistant.

This module provides a convenient CLI for interacting with the AI Mentor Assistant
features like recording, transcription, summarization, and knowledge base operations.
"""
import argparse
import sys
import os
from typing import Optional

from .config import Config
from . import capture, transcription, summarization, screen_record, knowledge_base
from backend.integrations.jira_manager import JiraManager


def _confirm(prompt: str, auto_confirm: bool) -> bool:
    """Prompt the user to confirm an action unless auto-confirmed."""
    if auto_confirm:
        return True
    response = input(f"{prompt} [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def cmd_record_audio(args) -> None:
    """Record audio command."""
    print(f"🎤 Recording audio for meeting: {args.meeting_id}")
    
    if args.duration:
        print(f"Recording for {args.duration} seconds...")
        audio_path = capture.capture_audio_only(args.meeting_id, args.duration)
    else:
        print("Recording until interrupted (Ctrl+C)...")
        audio_path = capture.capture_audio_only(args.meeting_id)
    
    print(f"✅ Audio saved: {audio_path}")
    
    if args.transcribe:
        print("🔤 Transcribing audio...")
        transcript = transcription.transcribe_audio(audio_path)
        
        if "error" not in transcript:
            print(f"✅ Transcription completed:")
            print(f"📝 {transcript.get('text', 'No text available')}")
            
            if args.summarize:
                print("📊 Generating summary...")
                summary = summarization.summarize_transcript(transcript)
                print(f"✅ Summary: {summary}")
        else:
            print(f"❌ Transcription failed: {transcript['error']}")


def cmd_transcribe(args) -> None:
    """Transcribe audio file command."""
    if not os.path.exists(args.audio_file):
        print(f"❌ Audio file not found: {args.audio_file}")
        return
    
    print(f"🔤 Transcribing: {args.audio_file}")
    transcript = transcription.transcribe_audio(args.audio_file)
    
    if "error" not in transcript:
        print(f"✅ Transcription completed:")
        print(f"📝 {transcript.get('text', 'No text available')}")
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(transcript.get('text', ''))
            print(f"💾 Transcript saved to: {args.output}")
        
        if args.summarize:
            print("📊 Generating summary...")
            summary = summarization.summarize_transcript(transcript)
            print(f"✅ Summary: {summary}")
    else:
        print(f"❌ Transcription failed: {transcript['error']}")


def cmd_screen_record(args) -> None:
    """Screen recording command."""
    print(f"🖥️ Recording screen for session: {args.session_id}")
    
    if args.duration:
        print(f"Recording for {args.duration} seconds...")
        video_path = screen_record.record_screen(args.session_id, args.duration)
    else:
        print("Recording until interrupted (Ctrl+C)...")
        video_path = screen_record.record_screen(args.session_id)
    
    print(f"✅ Screen recording saved: {video_path}")
    
    if args.analyze:
        print("🔍 Analyzing screen recording...")
        analysis = screen_record.analyze_screen_video(video_path)
        
        if analysis and not analysis[0].get("error"):
            result = analysis[0]
            print(f"✅ Analysis completed:")
            print(f"   Duration: {result.get('duration', 0):.2f} seconds")
            print(f"   Text segments: {len(result.get('text_segments', []))}")
            
            extracted_text = result.get('extracted_text', '')
            if extracted_text:
                print(f"   Extracted text: {extracted_text[:200]}...")
        else:
            error = analysis[0].get("error", "Unknown error") if analysis else "No results"
            print(f"❌ Analysis failed: {error}")


def cmd_screenshot(args) -> None:
    """Take screenshot command."""
    print("📸 Taking screenshot...")
    screenshot_path = screen_record.take_screenshot(args.filename)
    print(f"✅ Screenshot saved: {screenshot_path}")
    
    if args.extract_text:
        print("🔤 Extracting text from screenshot...")
        text = screen_record.extract_text_from_screenshot(screenshot_path)
        print(f"✅ Extracted text: {text}")


def cmd_kb_ingest(args) -> None:
    """Knowledge base ingestion command."""
    if args.repository:
        print(f"📚 Ingesting code repository: {args.repository}")
        result = knowledge_base.ingest_code_repository(args.repository)
        
        if "error" not in result:
            print(f"✅ Repository ingestion completed:")
            print(f"   Files ingested: {result['ingested_count']}")
            print(f"   Files failed: {result['failed_count']}")
        else:
            print(f"❌ Repository ingestion failed: {result['error']}")
    
    elif args.file:
        print(f"📄 Ingesting file: {args.file}")
        doc_id = knowledge_base.ingest_file(args.file, args.doc_type)
        
        if not doc_id.startswith("Failed"):
            print(f"✅ File ingested successfully: {doc_id}")
        else:
            print(f"❌ {doc_id}")
    
    elif args.text:
        print("📝 Ingesting text document...")
        knowledge_base.ingest_documents([args.text], args.doc_type)
        print("✅ Text document ingested")


def cmd_kb_search(args) -> None:
    """Knowledge base search command."""
    print(f"🔍 Searching knowledge base: '{args.query}'")
    
    results = knowledge_base.query_knowledge_base(
        args.query, 
        args.top_k, 
        args.doc_type if hasattr(args, 'doc_type') else None
    )
    
    if results:
        print(f"✅ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            if "error" not in result:
                score = result.get('similarity_score', 0)
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                
                print(f"\n{i}. Score: {score:.3f}")
                print(f"   Type: {metadata.get('type', 'unknown')}")
                print(f"   Source: {metadata.get('source', 'unknown')}")
                print(f"   Content: {content[:200]}..." if len(content) > 200 else f"   Content: {content}")
            else:
                print(f"\n{i}. Error: {result['error']}")
    else:
        print("❌ No results found")


def cmd_kb_stats(args) -> None:
    """Knowledge base statistics command."""
    print("📊 Knowledge Base Statistics:")
    stats = knowledge_base.get_knowledge_base_stats()
    
    for key, value in stats.items():
        print(f"   {key}: {value}")


def cmd_answer(args) -> None:
    """Answer question using knowledge base."""
    print(f"❓ Question: {args.question}")
    
    # Search knowledge base for context
    context_results = knowledge_base.query_knowledge_base(args.question, top_k=3)
    
    if context_results and "error" not in context_results[0]:
        # Combine context from search results
        context = " ".join([r.get('content', '') for r in context_results if 'content' in r])
        
        print("🧠 Answering using knowledge base context...")
        answer = summarization.answer_question(args.question, context)
        print(f"✅ Answer: {answer}")
    else:
        print("❌ No relevant context found in knowledge base")


def cmd_jira_comment(args) -> None:
    """Add comment to a JIRA issue."""
    if not _confirm(f"Add comment to {args.issue}?", args.yes):
        print("❌ Operation cancelled")
        return

    manager = JiraManager()
    try:
        manager.add_comment(args.issue, args.comment)
        print(f"💬 Comment added to {args.issue}")
    except Exception as e:
        print(f"❌ Failed to add comment: {e}")


def cmd_jira_transition(args) -> None:
    """Transition a JIRA issue's status."""
    if not _confirm(
        f"Transition issue {args.issue} with {args.transition_id}?", args.yes
    ):
        print("❌ Operation cancelled")
        return

    manager = JiraManager()
    try:
        manager.transition_issue(args.issue, args.transition_id, args.comment)
        print(f"🔀 Issue {args.issue} transitioned")
    except Exception as e:
        print(f"❌ Failed to transition issue: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI Mentor Assistant - Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record audio for 30 seconds and transcribe
  python -m app.cli record-audio meeting_001 --duration 30 --transcribe
  
  # Transcribe existing audio file
  python -m app.cli transcribe audio.wav --summarize
  
  # Record screen for 60 seconds and analyze
  python -m app.cli screen-record demo --duration 60 --analyze
  
  # Take screenshot and extract text
  python -m app.cli screenshot --extract-text
  
  # Ingest code repository into knowledge base
  python -m app.cli kb-ingest --repository /path/to/repo
  
  # Search knowledge base
  python -m app.cli kb-search "How to implement authentication?"
  
  # Answer question using knowledge base
  python -m app.cli answer "What is the project architecture?"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Record audio command
    record_parser = subparsers.add_parser('record-audio', help='Record audio from microphone')
    record_parser.add_argument('meeting_id', help='Meeting identifier')
    record_parser.add_argument('--duration', type=int, help='Recording duration in seconds')
    record_parser.add_argument('--transcribe', action='store_true', help='Transcribe recorded audio')
    record_parser.add_argument('--summarize', action='store_true', help='Summarize transcription')
    
    # Transcribe command
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio file')
    transcribe_parser.add_argument('audio_file', help='Path to audio file')
    transcribe_parser.add_argument('--output', help='Output file for transcript')
    transcribe_parser.add_argument('--summarize', action='store_true', help='Summarize transcription')
    
    # Screen record command
    screen_parser = subparsers.add_parser('screen-record', help='Record screen')
    screen_parser.add_argument('session_id', help='Session identifier')
    screen_parser.add_argument('--duration', type=int, help='Recording duration in seconds')
    screen_parser.add_argument('--analyze', action='store_true', help='Analyze recorded video')
    
    # Screenshot command
    screenshot_parser = subparsers.add_parser('screenshot', help='Take screenshot')
    screenshot_parser.add_argument('--filename', help='Screenshot filename')
    screenshot_parser.add_argument('--extract-text', action='store_true', help='Extract text from screenshot')
    
    # Knowledge base ingest command
    kb_ingest_parser = subparsers.add_parser('kb-ingest', help='Ingest content into knowledge base')
    kb_ingest_group = kb_ingest_parser.add_mutually_exclusive_group(required=True)
    kb_ingest_group.add_argument('--repository', help='Path to code repository')
    kb_ingest_group.add_argument('--file', help='Path to file to ingest')
    kb_ingest_group.add_argument('--text', help='Text content to ingest')
    kb_ingest_parser.add_argument('--doc-type', default='general', help='Document type')
    
    # Knowledge base search command
    kb_search_parser = subparsers.add_parser('kb-search', help='Search knowledge base')
    kb_search_parser.add_argument('query', help='Search query')
    kb_search_parser.add_argument('--top-k', type=int, default=5, help='Number of results to return')
    kb_search_parser.add_argument('--doc-type', help='Filter by document type')
    
    # Knowledge base stats command
    subparsers.add_parser('kb-stats', help='Show knowledge base statistics')
    
    # Answer question command
    answer_parser = subparsers.add_parser('answer', help='Answer question using knowledge base')
    answer_parser.add_argument('question', help='Question to answer')

    # JIRA comment command
    jira_comment = subparsers.add_parser(
        'jira-comment', help='Add comment to a JIRA issue'
    )
    jira_comment.add_argument('issue', help='JIRA issue key')
    jira_comment.add_argument('comment', help='Comment text')
    jira_comment.add_argument(
        '--yes',
        action='store_true',
        help='Bypass confirmation prompt and run non-interactively',
    )

    # JIRA transition command
    jira_transition = subparsers.add_parser(
        'jira-transition', help='Transition a JIRA issue'
    )
    jira_transition.add_argument('issue', help='JIRA issue key')
    jira_transition.add_argument('transition_id', help='Transition ID')
    jira_transition.add_argument('--comment', help='Optional comment to add')
    jira_transition.add_argument(
        '--yes',
        action='store_true',
        help='Bypass confirmation prompt and run non-interactively',
    )

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Commands that don't require API key
    local_commands = {'screenshot', 'kb-stats', 'jira-comment', 'jira-transition'}
    
    # Validate environment
    try:
        if args.command in local_commands:
            Config.validate_for_local_ops()
        else:
            Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        if args.command not in local_commands:
            print("Please check your .env file and ensure OPENAI_API_KEY is set.")
        return
    
    # Route to appropriate command handler
    command_handlers = {
        'record-audio': cmd_record_audio,
        'transcribe': cmd_transcribe,
        'screen-record': cmd_screen_record,
        'screenshot': cmd_screenshot,
        'kb-ingest': cmd_kb_ingest,
        'kb-search': cmd_kb_search,
        'kb-stats': cmd_kb_stats,
        'answer': cmd_answer,
        'jira-comment': cmd_jira_comment,
        'jira-transition': cmd_jira_transition,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n⏹️ Operation interrupted by user")
        except Exception as e:
            print(f"❌ Command failed: {str(e)}")
    else:
        print(f"❌ Unknown command: {args.command}")


if __name__ == "__main__":
    main()
