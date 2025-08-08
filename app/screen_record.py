"""Screen recording module.

This module provides screen recording and analysis capabilities using OpenCV
and other computer vision tools. It can capture screenshots, record screen
sessions, and analyze the recorded content.
"""
from __future__ import annotations

import logging
import os
import time
import threading
from datetime import datetime
from typing import List, Any, Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageGrab
import pytesseract

from .config import Config

logger = logging.getLogger(__name__)


class ScreenRecorder:
    """Screen recording using OpenCV and PIL."""
    
    def __init__(self):
        self.recording = False
        self.frames = []
        self.fps = Config.SCREEN_FPS
        self.output_path = ""
        
    def start_recording(self, output_path: str) -> None:
        """Start screen recording.
        
        Args:
            output_path: Path to save the recorded video.
        """
        self.recording = True
        self.frames = []
        self.output_path = output_path
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.start()
        logger.info(f"Screen recording started: {output_path}")
    
    def stop_recording(self) -> str:
        """Stop recording and save video.
        
        Returns:
            Path to the saved video file.
        """
        if not self.recording:
            return self.output_path
            
        self.recording = False
        self.recording_thread.join()
        
        if self.frames:
            self._save_video()
            logger.info(f"Screen recording saved: {self.output_path}")
        
        return self.output_path
    
    def _record_loop(self) -> None:
        """Main recording loop."""
        while self.recording:
            try:
                # Capture screenshot
                screenshot = ImageGrab.grab()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                self.frames.append(frame)
                
                # Wait for next frame
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                logger.error(f"Error capturing frame: {str(e)}")
                break
    
    def _save_video(self) -> None:
        """Save recorded frames as video."""
        if not self.frames:
            return
            
        # Get frame dimensions
        height, width, _ = self.frames[0].shape
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.output_path, fourcc, self.fps, (width, height))
        
        # Write frames
        for frame in self.frames:
            out.write(frame)
        
        out.release()


class ScreenAnalyzer:
    """Analyze screen recordings and screenshots."""

    def __init__(self, tesseract_path: Optional[str] = None) -> None:
        """Initialize the analyzer and configure Tesseract.

        Args:
            tesseract_path: Optional path to the Tesseract binary. If provided,
                this overrides environment and default path detection.
        """

        self.tesseract_cmd: Optional[str] = None

        # 1) Explicit parameter
        if tesseract_path:
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.tesseract_cmd = tesseract_path
            else:
                logger.error(
                    "Tesseract binary not found at override path: %s", tesseract_path
                )
        else:
            # 2) Environment variable
            env_path = os.environ.get("TESSERACT_CMD") or os.environ.get(
                "TESSERACT_PATH"
            )

            # 3) Common installation paths across platforms
            potential_paths = [p for p in [env_path] if p]
            potential_paths.extend(
                [
                    "/usr/bin/tesseract",
                    "/usr/local/bin/tesseract",
                    "/opt/homebrew/bin/tesseract",
                    "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                ]
            )

            for path in potential_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    self.tesseract_cmd = path
                    break

            if not self.tesseract_cmd:
                logger.error(
                    "Tesseract binary not found. Install Tesseract or set TESSERACT_CMD."
                )
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR.
        
        Args:
            image_path: Path to image file.
            
        Returns:
            Extracted text.
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {str(e)}")
            return f"OCR failed: {str(e)}"
    
    def extract_text_from_frame(self, frame: np.ndarray) -> str:
        """Extract text from video frame.
        
        Args:
            frame: OpenCV frame (numpy array).
            
        Returns:
            Extracted text.
        """
        try:
            # Convert BGR to RGB for PIL
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            text = pytesseract.image_to_string(image)
            return text.strip()
            
        except Exception as e:
            logger.error(f"Frame OCR failed: {str(e)}")
            return ""
    
    def analyze_video(self, video_path: str, sample_interval: int = 30) -> Dict[str, Any]:
        """Analyze video file for text and other content.
        
        Args:
            video_path: Path to video file.
            sample_interval: Analyze every Nth frame.
            
        Returns:
            Analysis results.
        """
        if not os.path.exists(video_path):
            return {"error": "Video file not found"}
        
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            extracted_texts = []
            frame_timestamps = []
            
            frame_num = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sample frames at intervals
                if frame_num % sample_interval == 0:
                    text = self.extract_text_from_frame(frame)
                    if text:  # Only store non-empty text
                        timestamp = frame_num / fps if fps > 0 else 0
                        extracted_texts.append(text)
                        frame_timestamps.append(timestamp)
                
                frame_num += 1
            
            cap.release()
            
            # Combine all extracted text
            all_text = " ".join(extracted_texts)
            
            return {
                "duration": duration,
                "frame_count": frame_count,
                "fps": fps,
                "extracted_text": all_text,
                "text_segments": [
                    {"timestamp": ts, "text": text}
                    for ts, text in zip(frame_timestamps, extracted_texts)
                ],
                "analysis_frames": len(extracted_texts)
            }
            
        except Exception as e:
            logger.error(f"Video analysis failed for {video_path}: {str(e)}")
            return {"error": str(e)}
    
    def detect_ui_elements(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect UI elements in a frame (basic implementation).
        
        Args:
            frame: OpenCV frame.
            
        Returns:
            List of detected UI elements.
        """
        elements = []
        
        try:
            # Convert to grayscale for processing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Simple edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours (basic button/window detection)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000:  # Filter small elements
                    x, y, w, h = cv2.boundingRect(contour)
                    elements.append({
                        "type": "rectangular_element",
                        "bbox": [x, y, w, h],
                        "area": area
                    })
            
        except Exception as e:
            logger.error(f"UI element detection failed: {str(e)}")
        
        return elements


def record_screen(session_id: str, duration: Optional[int] = None) -> str:
    """Record the screen during a session.

    Args:
        session_id: Identifier for the session (e.g. meeting ID or timestamp).
        duration: Recording duration in seconds. If None, records until stopped.

    Returns:
        Path to the recorded screen video file.
    """
    logger.info("Recording screen for session %s", session_id)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(Config.RECORDINGS_DIR, f"{session_id}_{timestamp}_screen.mp4")
    
    recorder = ScreenRecorder()
    
    try:
        recorder.start_recording(video_path)
        
        if duration:
            logger.info(f"Recording screen for {duration} seconds...")
            time.sleep(duration)
        else:
            logger.info("Recording screen. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Screen recording interrupted by user")
    finally:
        recorder.stop_recording()
    
    return video_path


def analyze_screen_video(video_path: str) -> List[Any]:
    """Analyze a recorded screen video and extract insights.

    Args:
        video_path: Path to the recorded screen video.

    Returns:
        A list of analysis results including extracted text and UI elements.
    """
    logger.info("Analyzing screen video at %s", video_path)
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return [{"error": "Video file not found"}]
    
    try:
        analyzer = ScreenAnalyzer()
        analysis = analyzer.analyze_video(video_path)
        
        # Format results as a list for compatibility
        results = [
            {
                "type": "video_analysis",
                "video_path": video_path,
                "duration": analysis.get("duration", 0),
                "extracted_text": analysis.get("extracted_text", ""),
                "text_segments": analysis.get("text_segments", []),
                "frame_count": analysis.get("frame_count", 0),
                "analysis_frames": analysis.get("analysis_frames", 0)
            }
        ]
        
        if "error" in analysis:
            results[0]["error"] = analysis["error"]
        
        logger.debug("Screen analysis completed with %d text segments", 
                    len(analysis.get("text_segments", [])))
        return results
        
    except Exception as e:
        logger.error(f"Screen video analysis failed: {str(e)}")
        return [{"error": str(e)}]


def take_screenshot(filename: Optional[str] = None) -> str:
    """Take a screenshot.
    
    Args:
        filename: Optional filename. If None, generates timestamp-based name.
        
    Returns:
        Path to the screenshot file.
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
    
    screenshot_path = os.path.join(Config.RECORDINGS_DIR, filename)
    
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
        
    except Exception as e:
        logger.error(f"Screenshot failed: {str(e)}")
        return f"Screenshot failed: {str(e)}"


def extract_text_from_screenshot(screenshot_path: str) -> str:
    """Extract text from a screenshot using OCR.
    
    Args:
        screenshot_path: Path to screenshot file.
        
    Returns:
        Extracted text.
    """
    logger.info(f"Extracting text from screenshot: {screenshot_path}")
    
    try:
        analyzer = ScreenAnalyzer()
        text = analyzer.extract_text_from_image(screenshot_path)
        logger.debug(f"Extracted text: {text[:100]}...")
        return text
        
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}")
        return f"Text extraction failed: {str(e)}"
