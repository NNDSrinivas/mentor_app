"""Private overlay system for AI interactions.

This creates a private UI overlay that appears only on the user's screen,
similar to how Zoom meeting controls are visible only to the host.
Other meeting participants cannot see these AI interactions.

The overlay attempts to detect active screen sharing sessions using
platform-specific hooks.  When sharing is detected the window is marked so
that it does not appear in the shared feed (when supported).  On platforms
without such APIs the overlay falls back to standard behavior, which may
include moving the window off screen or console output to avoid leaking
content.
"""
import asyncio
import json
import os
import platform
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
import logging

import psutil
import ctypes

# Windows display affinity flag to exclude window from screen capture
WDA_EXCLUDEFROMCAPTURE = 0x11

# Try to import tkinter, fall back to file-based system if not available
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    # Ensure names exist for type checkers/runtime guards
    tk = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]

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
        self.opacity = Config.OVERLAY_OPACITY
        self.opacity_scale = None
        self._was_screen_sharing = False
        
    def initialize(self):
        """Initialize the overlay system."""
        try:
            if TKINTER_AVAILABLE and tk is not None:
                # Create root window (hidden)
                self.root = tk.Tk()
                self.root.withdraw()  # Hide the main window
                self._bind_hotkeys()
                
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

    def _bind_hotkeys(self):
        """Bind global hotkeys for overlay controls."""
        if not TKINTER_AVAILABLE or self.fallback_mode or not self.root:
            return
        try:
            self.root.bind_all('<Control-Shift-o>', self.toggle_visibility)
            self.root.bind_all('<Control-Shift-Up>', lambda _e: self.adjust_opacity(0.1))
            self.root.bind_all('<Control-Shift-Down>', lambda _e: self.adjust_opacity(-0.1))
        except Exception as e:
            logger.error(f"Failed to bind hotkeys: {e}")

    # ------------------------------------------------------------------
    # Screen sharing detection
    # ------------------------------------------------------------------
    def _is_screen_sharing_active(self) -> bool:
        """Return True if an active screen sharing session is detected.

        Uses lightweight heuristics and OS specific hooks.  If detection
        fails or is unsupported, False is returned so that normal overlay
        behaviour continues.
        """
        try:
            system = platform.system().lower()
            if system == "darwin":
                return self._check_macos_sharing()
            if system == "windows":
                return self._check_windows_sharing()
            if system == "linux":
                return self._check_linux_sharing()
        except Exception as e:
            logger.debug(f"Screen sharing check failed: {e}")
        return False

    def _check_macos_sharing(self) -> bool:
        """Detect screen sharing on macOS via AppleScript hooks."""
        try:
            script = (
                'tell application "System Events" to return (exists '
                '(menu bar item "Stop Share" of menu 1 of menu bar item '
                '"Meeting" of menu bar 1 of process "zoom.us"))'
            )
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().lower() == "true"
        except Exception:
            pass
        return False

    def _check_windows_sharing(self) -> bool:
        """Detect screen sharing on Windows by inspecting running processes."""
        try:
            for proc in psutil.process_iter(["name", "cmdline"]):
                name = (proc.info.get("name") or "").lower()
                cmd = " ".join(proc.info.get("cmdline") or []).lower()
                if "zoom" in name and "sharing" in cmd:
                    return True
                if "teams" in name and ("sharing" in cmd or "--share" in cmd):
                    return True
        except Exception:
            pass
        return False

    def _check_linux_sharing(self) -> bool:
        """Detect screen sharing on Linux using process heuristics."""
        try:
            for proc in psutil.process_iter(["name", "cmdline"]):
                name = (proc.info.get("name") or "").lower()
                cmd = " ".join(proc.info.get("cmdline") or []).lower()
                if ("zoom" in name or "teams" in name) and (
                    "--share" in cmd or "sharing" in cmd
                ):
                    return True
        except Exception:
            pass
        return False

    def _apply_screen_share_exclusion(self):
        """Ensure overlay is not captured when screen sharing is active."""
        if not self.overlay_window:
            return

        system = platform.system().lower()
        try:
            if system == "windows":
                hwnd = self.overlay_window.winfo_id()
                success = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                if not success:
                    logger.warning("Failed to set window display affinity")
            elif system == "darwin":
                try:
                    from AppKit import NSApp, NSWindowSharingNone

                    window_id = int(self.overlay_window.winfo_id())
                    ns_window = NSApp().windowWithWindowNumber_(window_id)
                    if ns_window is not None:
                        ns_window.setSharingType_(NSWindowSharingNone)
                    else:
                        raise ValueError("NSWindow not found")
                except Exception as exc:
                    logger.debug(f"macOS exclusion failed: {exc}")
                    width = self.overlay_window.winfo_screenwidth()
                    height = self.overlay_window.winfo_screenheight()
                    self.overlay_window.geometry(f"+{width}+{height}")
            else:
                # Move the window off screen as a fallback to avoid capture
                width = self.overlay_window.winfo_screenwidth()
                height = self.overlay_window.winfo_screenheight()
                self.overlay_window.geometry(f"+{width}+{height}")
        except Exception as e:
            logger.debug(f"Failed to apply screen share exclusion: {e}")

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
                self._set_auto_hide_timer(Config.OVERLAY_AUTO_HIDE_SECONDS)
            
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
        if not TKINTER_AVAILABLE or self.fallback_mode or tk is None or ttk is None:
            return

        if self.overlay_window:
            self.overlay_window.destroy()

        self.overlay_window = tk.Toplevel(self.root)

        # Window configuration
        self.overlay_window.overrideredirect(True)  # Remove window decorations
        self.overlay_window.attributes('-topmost', True)  # Always on top
        self.overlay_window.attributes('-alpha', self.opacity)  # Configurable transparency

        # Make window stay on top even during screen sharing
        try:
            # macOS specific
            self.overlay_window.attributes('-transparentcolor', '')
        except Exception:
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

        # Opacity slider
        self.opacity_scale = tk.Scale(
            self.main_frame, from_=20, to=100, orient=tk.HORIZONTAL,
            command=self._on_opacity_change, bg='#2b2b2b', fg='#00ff88',
            highlightthickness=0, length=100
        )
        self.opacity_scale.set(int(self.opacity * 100))
        self.opacity_scale.pack(anchor=tk.E, pady=(5, 0))

        # Apply screen share exclusion in case sharing is already active
        self._apply_screen_share_exclusion()
    
    def _update_content(self, content: str, content_type: str):
        """Update overlay content."""
        if not TKINTER_AVAILABLE or self.fallback_mode or not self.overlay_window or ttk is None or tk is None:
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
            if self._is_screen_sharing_active():
                self._apply_screen_share_exclusion()
            self.overlay_window.deiconify()
            self.is_visible = True

    def toggle_visibility(self, _event=None):
        """Toggle overlay visibility via hotkey."""
        if self.is_visible:
            self.hide_overlay()
        else:
            if self.overlay_window:
                self._show_window()
            elif self.current_content:
                self.show_ai_response(self.current_content)

    def adjust_opacity(self, delta: float):
        """Incrementally adjust window opacity."""
        self.opacity = max(0.2, min(1.0, self.opacity + delta))
        if self.overlay_window:
            self.overlay_window.attributes('-alpha', self.opacity)
        if self.opacity_scale:
            self.opacity_scale.set(int(self.opacity * 100))

    def _on_opacity_change(self, value):
        """Callback for opacity slider changes."""
        try:
            self.opacity = max(0.2, min(1.0, float(value) / 100))
            if self.overlay_window:
                self.overlay_window.attributes('-alpha', self.opacity)
        except Exception as e:
            logger.error(f"Opacity change error: {e}")
    
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
                is_sharing = self._is_screen_sharing_active()
                if is_sharing:
                    self._apply_screen_share_exclusion()
                self._was_screen_sharing = is_sharing

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
                is_sharing = self._is_screen_sharing_active()
                if is_sharing:
                    self._apply_screen_share_exclusion()
                self._was_screen_sharing = is_sharing

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
