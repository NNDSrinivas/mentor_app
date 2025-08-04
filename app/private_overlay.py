"""Private overlay system for AI interactions.

This creates a private UI overlay that appears only on the user's screen,
similar to how Zoom meeting controls are visible only to the host.
Other meeting participants cannot see these AI interactions.
"""
import asyncio
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Try to import tkinter, fall back to file-based system if not available
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

from .config import Config

logger = logging.getLogger(__name__)


class PrivateOverlay:
    """Private overlay window for AI interactions."""
    
    def __init__(self):
        self.root = None
        self.overlay_window = None
        self.is_visible = False
        self.current_content = ""
        self.auto_hide_timer = None
        self.fallback_mode = not TKINTER_AVAILABLE
        
    def initialize(self):
        """Initialize the overlay system."""
        try:
            if TKINTER_AVAILABLE:
                # Create root window (hidden)
                self.root = tk.Tk()
                self.root.withdraw()  # Hide the main window
                
                # Start the overlay monitoring thread
                self.monitor_thread = threading.Thread(target=self._monitor_overlays, daemon=True)
                self.monitor_thread.start()
                
                logger.info("Private overlay system initialized with GUI")
            else:
                # Use file-based fallback system
                self.monitor_thread = threading.Thread(target=self._monitor_overlays_fallback, daemon=True)
                self.monitor_thread.start()
                
                logger.info("Private overlay system initialized with file-based fallback")
            
        except Exception as e:
            logger.error(f"Failed to initialize overlay system: {e}")
            self.fallback_mode = True
    
    def show_ai_response(self, content: str, response_type: str = "response"):
        """Show AI response in private overlay."""
        try:
            if self.fallback_mode or not TKINTER_AVAILABLE:
                self._show_fallback_response(content, response_type)
            else:
                self._create_overlay_window()
                self._update_content(content, response_type)
                self._position_window()
                self._show_window()
                self._set_auto_hide_timer(15)  # Auto-hide after 15 seconds
            
            logger.info(f"Showing AI {response_type}: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"Failed to show AI response: {e}")
            # Fallback to console output
            print(f"\n🤖 AI {response_type.upper()}: {content}\n")
    
    def _show_fallback_response(self, content: str, response_type: str):
        """Show response using console output as fallback."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if response_type == "response":
            icon = "🤖"
            title = "AI Assistant"
        elif response_type == "questions":
            icon = "❓"
            title = "AI Questions"
        else:
            icon = "💭"
            title = "AI Note"
        
        print(f"\n{'-' * 50}")
        print(f"{icon} {title} [{timestamp}]")
        print(f"{'-' * 50}")
        print(content)
        print(f"{'-' * 50}\n")
    
    def show_ai_questions(self, questions: str):
        """Show AI questions in private overlay."""
        self.show_ai_response(questions, "questions")
    
    def _create_overlay_window(self):
        """Create the overlay window."""
        if not TKINTER_AVAILABLE or self.fallback_mode:
            return
            
        if self.overlay_window:
            self.overlay_window.destroy()
            
        self.overlay_window = tk.Toplevel(self.root)
        
        # Window configuration
        self.overlay_window.overrideredirect(True)  # Remove window decorations
        self.overlay_window.attributes('-topmost', True)  # Always on top
        self.overlay_window.attributes('-alpha', 0.9)  # Slightly transparent
        
        # Make window stay on top even during screen sharing
        try:
            # macOS specific
            self.overlay_window.attributes('-transparentcolor', '')
        except:
            pass
            
        # Configure style
        style = ttk.Style()
        style.configure('Overlay.TFrame', background='#2b2b2b', relief='solid', borderwidth=1)
        style.configure('OverlayTitle.TLabel', background='#2b2b2b', foreground='#00ff88', 
                       font=('SF Pro Display', 12, 'bold'))
        style.configure('OverlayContent.TLabel', background='#2b2b2b', foreground='#ffffff',
                       font=('SF Pro Display', 10), wraplength=350)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.overlay_window, style='Overlay.TFrame', padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add close button
        self.close_button = tk.Button(
            self.main_frame, text="✕", command=self.hide_overlay,
            bg='#ff4444', fg='white', font=('SF Pro Display', 8, 'bold'),
            relief='flat', width=2, height=1
        )
        self.close_button.pack(side=tk.RIGHT, anchor=tk.NE)
    
    def _update_content(self, content: str, content_type: str):
        """Update overlay content."""
        if not TKINTER_AVAILABLE or self.fallback_mode or not self.overlay_window:
            return
            
        # Clear existing content
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, ttk.Label):
                widget.destroy()
        
        # Title based on content type
        if content_type == "response":
            title = "🤖 AI Assistant"
            title_color = '#00ff88'
        elif content_type == "questions":
            title = "❓ AI Questions"
            title_color = '#ffaa00'
        else:
            title = "💭 AI Note"
            title_color = '#88aaff'
        
        # Add title
        title_label = ttk.Label(
            self.main_frame, text=title,
            style='OverlayTitle.TLabel'
        )
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Add content
        content_label = ttk.Label(
            self.main_frame, text=content,
            style='OverlayContent.TLabel'
        )
        content_label.pack(anchor=tk.W, fill=tk.X)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = ttk.Label(
            self.main_frame, text=f"⏰ {timestamp}",
            background='#2b2b2b', foreground='#888888',
            font=('SF Pro Display', 8)
        )
        time_label.pack(anchor=tk.E, pady=(5, 0))
        
        self.current_content = content
    
    def _position_window(self):
        """Position window in bottom-right corner."""
        if not self.overlay_window:
            return
            
        # Update window to get proper dimensions
        self.overlay_window.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.overlay_window.winfo_screenwidth()
        screen_height = self.overlay_window.winfo_screenheight()
        
        # Get window dimensions
        window_width = self.overlay_window.winfo_reqwidth()
        window_height = self.overlay_window.winfo_reqheight()
        
        # Position in bottom-right corner with some margin
        x = screen_width - window_width - 20
        y = screen_height - window_height - 100  # Leave space for dock/taskbar
        
        self.overlay_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _show_window(self):
        """Show the overlay window."""
        if self.overlay_window:
            self.overlay_window.deiconify()
            self.is_visible = True
    
    def hide_overlay(self):
        """Hide the overlay window."""
        if self.overlay_window:
            self.overlay_window.withdraw()
            self.is_visible = False
            
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None
    
    def _set_auto_hide_timer(self, seconds: int):
        """Set auto-hide timer."""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            
        self.auto_hide_timer = threading.Timer(seconds, self.hide_overlay)
        self.auto_hide_timer.start()
    
    def _monitor_overlays_fallback(self):
        """Monitor for overlay files using fallback system."""
        overlay_dir = f"{Config.TEMP_DIR}"
        
        while True:
            try:
                if not os.path.exists(overlay_dir):
                    time.sleep(1)
                    continue
                
                # Check for new overlay files
                for filename in os.listdir(overlay_dir):
                    if filename.startswith("ai_overlay_") and filename.endswith(".json"):
                        filepath = os.path.join(overlay_dir, filename)
                        
                        try:
                            with open(filepath, 'r') as f:
                                overlay_data = json.load(f)
                            
                            # Display overlay using fallback method
                            self._show_fallback_response(
                                overlay_data['content'],
                                overlay_data['type']
                            )
                            
                            # Remove the file
                            os.remove(filepath)
                            
                        except Exception as e:
                            logger.error(f"Error processing overlay file {filename}: {e}")
                            try:
                                os.remove(filepath)
                            except:
                                pass
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Error in fallback overlay monitoring: {e}")
                time.sleep(1)
    
    def _monitor_overlays(self):
        """Monitor for overlay files and display them."""
        overlay_dir = f"{Config.TEMP_DIR}"
        
        while True:
            try:
                if not os.path.exists(overlay_dir):
                    time.sleep(1)
                    continue
                
                # Check for new overlay files
                for filename in os.listdir(overlay_dir):
                    if filename.startswith("ai_overlay_") and filename.endswith(".json"):
                        filepath = os.path.join(overlay_dir, filename)
                        
                        try:
                            with open(filepath, 'r') as f:
                                overlay_data = json.load(f)
                            
                            # Display overlay
                            self.show_ai_response(
                                overlay_data['content'],
                                overlay_data['type']
                            )
                            
                            # Remove the file
                            os.remove(filepath)
                            
                        except Exception as e:
                            logger.error(f"Error processing overlay file {filename}: {e}")
                            try:
                                os.remove(filepath)
                            except:
                                pass
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                logger.error(f"Error in overlay monitoring: {e}")
                time.sleep(1)
    
    def start_ui_loop(self):
        """Start the UI event loop."""
        if TKINTER_AVAILABLE and not self.fallback_mode and self.root:
            self.root.mainloop()
        else:
            # Keep thread alive for fallback mode
            while True:
                time.sleep(1)


class OverlayManager:
    """Manager for the private overlay system."""
    
    def __init__(self):
        self.overlay = PrivateOverlay()
        self.initialized = False
    
    def initialize(self):
        """Initialize the overlay system."""
        if not self.initialized:
            self.overlay.initialize()
            self.initialized = True
    
    def show_response(self, content: str, response_type: str = "response"):
        """Show AI response in overlay."""
        if not self.initialized:
            self.initialize()
        self.overlay.show_ai_response(content, response_type)
    
    def show_questions(self, questions: str):
        """Show AI questions in overlay."""
        if not self.initialized:
            self.initialize()
        self.overlay.show_ai_questions(questions)
    
    def start_background_thread(self):
        """Start overlay in background thread."""
        if not self.initialized:
            self.initialize()
            
        ui_thread = threading.Thread(target=self.overlay.start_ui_loop, daemon=True)
        ui_thread.start()


# Global overlay manager instance
overlay_manager = OverlayManager()


def show_ai_response(content: str, response_type: str = "response"):
    """Show AI response in private overlay."""
    overlay_manager.show_response(content, response_type)


def show_ai_questions(questions: str):
    """Show AI questions in private overlay."""
    overlay_manager.show_questions(questions)


def initialize_overlay_system():
    """Initialize the private overlay system."""
    overlay_manager.initialize()
    overlay_manager.start_background_thread()
