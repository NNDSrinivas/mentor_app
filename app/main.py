"""Main entry point for the AI Mentor Assistant.

This script demonstrates the full functionality of the AI Mentor Assistant,
including real audio recording, transcription, summarization, screen recording,
and knowledge base integration.
"""
import logging
import os
import sys
from typing import Optional

from .config import Config
from . import capture, transcription, summarization, screen_record, knowledge_base


def configure_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("mentor_app.log")
        ]
    )


def setup_environment() -> bool:
    """Setup and validate the environment."""
    try:
        Config.validate()
        logging.info("Environment validation successful")
        return True
    except ValueError as e:
        logging.error(f"Environment validation failed: {e}")
        print(f"❌ Setup Error: {e}")
        print("\n📝 Please create a .env file with your OpenAI API key:")
        print("   cp .env.template .env")
        print("   # Edit .env and add your OPENAI_API_KEY")
        return False


def demo_audio_recording_and_transcription() -> Optional[dict]:
    """Demo audio recording and transcription."""
    print("\n🎤 Audio Recording & Transcription Demo")
    print("=" * 50)
    
    try:
        # Test microphone first
        print("Testing microphone for 3 seconds...")
        test_path = capture.capture_microphone_test(3)
        print(f"✅ Microphone test completed: {test_path}")
        
        # Record audio for demo
        print("\nRecording audio for 5 seconds...")
        audio_path = capture.capture_audio_only("demo_meeting", 5)
        print(f"✅ Audio recorded: {audio_path}")
        
        # Transcribe audio
        print("Transcribing audio...")
        transcript = transcription.transcribe_audio(audio_path)
        
        if "error" in transcript:
            print(f"❌ Transcription failed: {transcript['error']}")
            return None
        
        print(f"✅ Transcription completed")
        print(f"📝 Transcript: {transcript.get('text', 'No text available')}")
        
        return transcript
        
    except Exception as e:
        print(f"❌ Audio demo failed: {str(e)}")
        return None


def demo_summarization(transcript: dict) -> None:
    """Demo summarization features."""
    print("\n📊 Summarization Demo")
    print("=" * 50)
    
    try:
        # Generate summary
        print("Generating summary...")
        summary = summarization.summarize_transcript(transcript)
        print(f"✅ Summary:\n{summary}\n")
        
        # Extract action items
        print("Extracting action items...")
        action_items = summarization.extract_action_items(transcript)
        print("✅ Action Items:")
        for i, item in enumerate(action_items, 1):
            print(f"   {i}. {item}")
        
        # Extract decisions
        print("\nExtracting decisions...")
        decisions = summarization.extract_decisions(transcript)
        print("✅ Decisions:")
        for i, decision in enumerate(decisions, 1):
            print(f"   {i}. {decision}")
        
        # Answer a question
        print("\nAnswering question about the transcript...")
        question = "What was the main topic discussed?"
        answer = summarization.answer_question(question, transcript.get("text", ""))
        print(f"✅ Q: {question}")
        print(f"   A: {answer}")
        
    except Exception as e:
        print(f"❌ Summarization demo failed: {str(e)}")


def demo_screen_recording() -> Optional[str]:
    """Demo screen recording."""
    print("\n🖥️  Screen Recording Demo")
    print("=" * 50)
    
    try:
        # Take a screenshot first
        print("Taking screenshot...")
        screenshot_path = screen_record.take_screenshot()
        print(f"✅ Screenshot saved: {screenshot_path}")
        
        # Extract text from screenshot
        print("Extracting text from screenshot...")
        screenshot_text = screen_record.extract_text_from_screenshot(screenshot_path)
        print(f"✅ Extracted text: {screenshot_text[:100]}..." if len(screenshot_text) > 100 else f"✅ Extracted text: {screenshot_text}")
        
        # Record screen for a short duration
        print("Recording screen for 5 seconds...")
        video_path = screen_record.record_screen("demo_session", 5)
        print(f"✅ Screen recording saved: {video_path}")
        
        return video_path
        
    except Exception as e:
        print(f"❌ Screen recording demo failed: {str(e)}")
        return None


def demo_screen_analysis(video_path: str) -> None:
    """Demo screen video analysis."""
    print("\n🔍 Screen Analysis Demo")
    print("=" * 50)
    
    try:
        print("Analyzing screen recording...")
        analysis_results = screen_record.analyze_screen_video(video_path)
        
        if analysis_results and not analysis_results[0].get("error"):
            result = analysis_results[0]
            print(f"✅ Analysis completed:")
            print(f"   Duration: {result.get('duration', 0):.2f} seconds")
            print(f"   Frames analyzed: {result.get('analysis_frames', 0)}")
            
            extracted_text = result.get('extracted_text', '')
            if extracted_text:
                print(f"   Extracted text: {extracted_text[:200]}..." if len(extracted_text) > 200 else f"   Extracted text: {extracted_text}")
            else:
                print("   No text extracted from video")
        else:
            error = analysis_results[0].get("error", "Unknown error") if analysis_results else "No results"
            print(f"❌ Analysis failed: {error}")
            
    except Exception as e:
        print(f"❌ Screen analysis demo failed: {str(e)}")


def demo_knowledge_base() -> None:
    """Demo knowledge base functionality."""
    print("\n🧠 Knowledge Base Demo")
    print("=" * 50)
    
    try:
        # Get knowledge base stats
        stats = knowledge_base.get_knowledge_base_stats()
        print(f"📊 Knowledge base stats: {stats.get('document_count', 0)} documents")
        
        # Ingest some sample documents
        print("Ingesting sample documents...")
        sample_docs = [
            "This is a sample meeting transcript about project planning and resource allocation.",
            "Code review guidelines: Always check for security vulnerabilities and performance issues.",
            "Architecture overview: The system uses a microservices architecture with API Gateway."
        ]
        
        knowledge_base.ingest_documents(sample_docs, "demo")
        print("✅ Sample documents ingested")
        
        # Try to ingest this README file
        readme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")
        if os.path.exists(readme_path):
            print("Ingesting README.md...")
            doc_id = knowledge_base.ingest_file(readme_path, "documentation")
            if not doc_id.startswith("Failed"):
                print(f"✅ README.md ingested as {doc_id[:8]}...")
            else:
                print(f"❌ {doc_id}")
        
        # Query the knowledge base
        print("\nQuerying knowledge base...")
        query = "What is the architecture of the system?"
        results = knowledge_base.query_knowledge_base(query, top_k=3)
        
        print(f"✅ Query: '{query}'")
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            if "error" not in result:
                score = result.get('similarity_score', 0)
                content_preview = result.get('content', '')[:100] + "..." if len(result.get('content', '')) > 100 else result.get('content', '')
                print(f"   {i}. (Score: {score:.3f}) {content_preview}")
            else:
                print(f"   {i}. Error: {result['error']}")
        
    except Exception as e:
        print(f"❌ Knowledge base demo failed: {str(e)}")


def demo_integrated_workflow() -> None:
    """Demo integrated workflow combining all features."""
    print("\n🔄 Integrated Workflow Demo")
    print("=" * 50)
    
    try:
        # Simulate a complete workflow
        print("1. Recording meeting audio (3 seconds)...")
        audio_path = capture.capture_audio_only("integrated_demo", 3)
        
        print("2. Transcribing audio...")
        transcript = transcription.transcribe_audio(audio_path)
        
        if transcript and "error" not in transcript:
            print("3. Generating meeting report...")
            report = summarization.generate_meeting_report(transcript)
            
            print("✅ Meeting Report Generated:")
            print(f"   Summary: {report.get('summary', 'N/A')[:100]}...")
            print(f"   Action Items: {len(report.get('action_items', []))}")
            print(f"   Decisions: {len(report.get('decisions', []))}")
            
            # Add transcript to knowledge base
            print("4. Adding transcript to knowledge base...")
            transcript_content = f"Meeting Summary: {report.get('summary', '')}\n\nFull Transcript: {transcript.get('text', '')}"
            metadata = {
                "type": "meeting_transcript",
                "source": "integrated_demo",
                "has_summary": True,
                "action_items_count": len(report.get('action_items', [])),
                "decisions_count": len(report.get('decisions', []))
            }
            
            kb = knowledge_base.KnowledgeBase()
            doc_id = kb.add_document(transcript_content, metadata)
            print(f"✅ Transcript added to knowledge base: {doc_id[:8]}...")
            
        else:
            print("❌ Transcription failed, skipping report generation")
        
        print("5. Taking screenshot for documentation...")
        screenshot_path = screen_record.take_screenshot("integrated_demo.png")
        print(f"✅ Screenshot saved: {screenshot_path}")
        
        print("\n🎉 Integrated workflow completed successfully!")
        
    except Exception as e:
        print(f"❌ Integrated workflow failed: {str(e)}")


def interactive_menu() -> None:
    """Interactive menu for testing features."""
    while True:
        print("\n🤖 AI Mentor Assistant - Interactive Demo")
        print("=" * 50)
        print("1. Audio Recording & Transcription")
        print("2. Screen Recording & Analysis")
        print("3. Knowledge Base Operations")
        print("4. Run Full Integrated Demo")
        print("5. View Knowledge Base Stats")
        print("0. Exit")
        
        choice = input("\nSelect an option (0-5): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            transcript = demo_audio_recording_and_transcription()
            if transcript:
                demo_summarization(transcript)
        elif choice == "2":
            video_path = demo_screen_recording()
            if video_path:
                demo_screen_analysis(video_path)
        elif choice == "3":
            demo_knowledge_base()
        elif choice == "4":
            demo_integrated_workflow()
        elif choice == "5":
            stats = knowledge_base.get_knowledge_base_stats()
            print(f"\n📊 Knowledge Base Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Invalid option. Please try again.")


def run_demo() -> None:
    """Run a comprehensive demo of all features."""
    print("🚀 AI Mentor Assistant - Full Demo")
    print("=" * 50)
    
    # Audio recording and transcription
    transcript = demo_audio_recording_and_transcription()
    
    # Summarization (if transcription was successful)
    if transcript:
        demo_summarization(transcript)
    
    # Screen recording
    video_path = demo_screen_recording()
    
    # Screen analysis (if recording was successful)
    if video_path:
        demo_screen_analysis(video_path)
    
    # Knowledge base
    demo_knowledge_base()
    
    # Integrated workflow
    demo_integrated_workflow()
    
    print("\n✨ Demo completed! Check the logs and output files.")
    print(f"📁 Recordings saved in: {Config.RECORDINGS_DIR}")
    print(f"📁 Knowledge base stored in: {Config.CHROMA_PERSIST_DIR}")


def main() -> None:
    """Main entry point."""
    configure_logging()
    
    print("🤖 AI Mentor Assistant")
    print("=" * 50)
    
    # Setup environment
    if not setup_environment():
        return
    
    print(f"✅ Environment setup complete")
    print(f"📁 Recordings directory: {Config.RECORDINGS_DIR}")
    print(f"🧠 Knowledge base directory: {Config.CHROMA_PERSIST_DIR}")
    
    # Check if we should run interactively or as a demo
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_menu()
    else:
        run_demo()


if __name__ == "__main__":
    main()
