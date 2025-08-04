"""
Desktop Application Support for AI Interview Assistant

This module provides support for desktop meeting applications by:
1. Creating a standalone desktop overlay
2. Using OS-level audio capture
3. Providing universal screen positioning
4. Supporting all major meeting platforms
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import json
import requests
import queue
import pyaudio
import wave
import numpy as np
from typing import Optional, Dict, Any
import os
import sys
import subprocess
import psutil

class DesktopInterviewAssistant:
    """Desktop overlay for meeting applications."""
    
    def __init__(self):
        self.root = None
        self.overlay_window = None
        self.is_stealth_mode = False
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.current_question = ""
        self.current_answer = ""
        
        # Audio settings
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio = None
        self.stream = None
        
        # Meeting detection
        self.detected_meeting_apps = []
        self.meeting_app_processes = {
            'zoom': ['zoom.exe', 'zoom', 'Zoom.app'],
            'teams': ['Teams.exe', 'teams', 'Microsoft Teams.app'],
            'webex': ['CiscoCollabHost.exe', 'webex', 'Webex.app'],
            'skype': ['Skype.exe', 'skype', 'Skype.app'],
            'discord': ['Discord.exe', 'discord', 'Discord.app'],
            'slack': ['slack.exe', 'slack', 'Slack.app']
        }
        
        self.init_desktop_overlay()
    
    def init_desktop_overlay(self):
        """Initialize the desktop overlay window."""
        
        self.root = tk.Tk()
        self.root.title("AI Interview Assistant")
        
        # Configure window properties for desktop overlay
        self.setup_overlay_window()
        
        # Create UI components
        self.create_ui_components()
        
        # Start meeting detection
        self.start_meeting_detection()
        
        # Start audio monitoring
        self.init_audio_capture()
        
        print("🖥️ Desktop Interview Assistant initialized")
    
    def setup_overlay_window(self):
        """Configure the overlay window for desktop use."""
        
        # Window dimensions
        window_width = 600
        window_height = 800
        
        # Position on right side of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x_position = screen_width - window_width - 20
        y_position = 20
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Configure for always on top
        self.root.attributes('-topmost', True)
        
        # Configure transparency for stealth mode
        self.root.attributes('-alpha', 0.95)
        
        # Configure window style
        self.root.configure(bg='black')
        
        # Prevent window from being minimized accidentally
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Key bindings for stealth mode
        self.root.bind('<Control-Shift-A>', self.toggle_stealth_mode)
        
        print("🪟 Desktop overlay window configured")
    
    def create_ui_components(self):
        """Create the UI components for the desktop overlay."""
        
        # Main frame with dark theme
        main_frame = tk.Frame(self.root, bg='black', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = tk.Frame(main_frame, bg='black')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(
            header_frame, 
            text="🤖 AI Interview Assistant (Desktop)", 
            font=('Courier New', 14, 'bold'),
            fg='#00ff00',
            bg='black'
        )
        title_label.pack(side=tk.LEFT)
        
        # Stealth mode indicator
        self.stealth_indicator = tk.Label(
            header_frame,
            text="👁️ VISIBLE",
            font=('Courier New', 10),
            fg='#00ff00',
            bg='black'
        )
        self.stealth_indicator.pack(side=tk.RIGHT)
        
        # Status frame
        status_frame = tk.Frame(main_frame, bg='black')
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(
            status_frame,
            text="🔄 Initializing...",
            font=('Courier New', 10),
            fg='#888888',
            bg='black'
        )
        self.status_label.pack()
        
        # Meeting detection frame
        meeting_frame = tk.Frame(main_frame, bg='black', relief=tk.RIDGE, bd=1)
        meeting_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            meeting_frame,
            text="Detected Meeting Apps:",
            font=('Courier New', 10, 'bold'),
            fg='#00ff00',
            bg='black'
        ).pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.meeting_apps_label = tk.Label(
            meeting_frame,
            text="Scanning...",
            font=('Courier New', 9),
            fg='#888888',
            bg='black',
            wraplength=580
        )
        self.meeting_apps_label.pack(anchor=tk.W, padx=5, pady=(0, 5))
        
        # Interview configuration frame
        config_frame = tk.Frame(main_frame, bg='black', relief=tk.RIDGE, bd=1)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            config_frame,
            text="Interview Configuration:",
            font=('Courier New', 10, 'bold'),
            fg='#00ff00',
            bg='black'
        ).pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        # Interview level selection
        level_frame = tk.Frame(config_frame, bg='black')
        level_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(level_frame, text="Level:", font=('Courier New', 9), fg='#888888', bg='black').pack(side=tk.LEFT)
        
        self.level_var = tk.StringVar(value="IC6")
        level_combo = ttk.Combobox(
            level_frame,
            textvariable=self.level_var,
            values=["IC5", "IC6", "IC7", "E5", "E6", "E7"],
            width=15,
            state="readonly"
        )
        level_combo.pack(side=tk.LEFT, padx=(5, 0))
        level_combo.bind('<<ComboboxSelected>>', self.on_config_change)
        
        # Company selection
        company_frame = tk.Frame(config_frame, bg='black')
        company_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(company_frame, text="Company:", font=('Courier New', 9), fg='#888888', bg='black').pack(side=tk.LEFT)
        
        self.company_var = tk.StringVar(value="")
        company_combo = ttk.Combobox(
            company_frame,
            textvariable=self.company_var,
            values=["", "Meta", "Google", "Amazon", "Microsoft", "Apple", "Netflix"],
            width=15,
            state="readonly"
        )
        company_combo.pack(side=tk.LEFT, padx=(5, 0))
        company_combo.bind('<<ComboboxSelected>>', self.on_config_change)
        
        # Audio status
        audio_frame = tk.Frame(config_frame, bg='black')
        audio_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        
        self.audio_status = tk.Label(
            audio_frame,
            text="🎤 Audio: Initializing...",
            font=('Courier New', 9),
            fg='#888888',
            bg='black'
        )
        self.audio_status.pack(side=tk.LEFT)
        
        # Question display
        question_frame = tk.Frame(main_frame, bg='black', relief=tk.RIDGE, bd=1)
        question_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            question_frame,
            text="Current Question:",
            font=('Courier New', 10, 'bold'),
            fg='#0066ff',
            bg='black'
        ).pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.question_display = tk.Text(
            question_frame,
            height=3,
            font=('Courier New', 10),
            fg='#0066ff',
            bg='#001122',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.question_display.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Answer display
        answer_frame = tk.Frame(main_frame, bg='black', relief=tk.RIDGE, bd=1)
        answer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(
            answer_frame,
            text="AI Response:",
            font=('Courier New', 10, 'bold'),
            fg='#00ff00',
            bg='black'
        ).pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        # Create scrollable text widget
        text_frame = tk.Frame(answer_frame, bg='black')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.answer_display = tk.Text(
            text_frame,
            font=('Courier New', 11),
            fg='#00ff00',
            bg='#002200',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.answer_display.yview)
        self.answer_display.configure(yscrollcommand=scrollbar.set)
        
        self.answer_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons
        controls_frame = tk.Frame(main_frame, bg='black')
        controls_frame.pack(fill=tk.X)
        
        # Manual input
        input_frame = tk.Frame(controls_frame, bg='black')
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.manual_input = tk.Entry(
            input_frame,
            font=('Courier New', 10),
            fg='#00ff00',
            bg='#002200',
            insertbackground='#00ff00'
        )
        self.manual_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.manual_input.bind('<Return>', self.handle_manual_question)
        
        test_btn = tk.Button(
            input_frame,
            text="🧪 Test",
            command=self.handle_manual_question,
            font=('Courier New', 9, 'bold'),
            fg='black',
            bg='#00ff00',
            width=8
        )
        test_btn.pack(side=tk.RIGHT)
        
        # Stealth and control buttons
        button_frame = tk.Frame(controls_frame, bg='black')
        button_frame.pack(fill=tk.X)
        
        stealth_btn = tk.Button(
            button_frame,
            text="🕵️ Toggle Stealth (Ctrl+Shift+A)",
            command=self.toggle_stealth_mode,
            font=('Courier New', 9),
            fg='white',
            bg='#ff6b6b',
            width=25
        )
        stealth_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        minimize_btn = tk.Button(
            button_frame,
            text="📦 Minimize",
            command=self.minimize_window,
            font=('Courier New', 9),
            fg='black',
            bg='#888888',
            width=10
        )
        minimize_btn.pack(side=tk.RIGHT)
        
        print("🎨 Desktop UI components created")
    
    def start_meeting_detection(self):
        """Start detecting running meeting applications."""
        
        def detect_loop():
            while True:
                try:
                    detected = self.detect_meeting_applications()
                    self.detected_meeting_apps = detected
                    
                    if detected:
                        apps_text = ", ".join(detected)
                        self.meeting_apps_label.config(text=f"✅ {apps_text}", fg='#00ff00')
                        self.status_label.config(text="🎯 Meeting apps detected - Ready for assistance")
                    else:
                        self.meeting_apps_label.config(text="❌ No meeting apps detected", fg='#ff6b6b')
                        self.status_label.config(text="⏳ Waiting for meeting application...")
                    
                    time.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    print(f"❌ Error in meeting detection: {e}")
                    time.sleep(10)
        
        detection_thread = threading.Thread(target=detect_loop, daemon=True)
        detection_thread.start()
        
        print("🔍 Meeting detection started")
    
    def detect_meeting_applications(self):
        """Detect currently running meeting applications."""
        
        detected = []
        
        try:
            # Get all running processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    process_name = proc.info['name'].lower()
                    
                    for app_name, process_names in self.meeting_app_processes.items():
                        for proc_pattern in process_names:
                            if proc_pattern.lower() in process_name:
                                if app_name not in detected:
                                    detected.append(app_name.title())
                                break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"❌ Error detecting processes: {e}")
        
        return detected
    
    def init_audio_capture(self):
        """Initialize audio capture for desktop applications."""
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # Find default input device
            device_info = self.audio.get_default_input_device_info()
            print(f"🎤 Using audio device: {device_info['name']}")
            
            # Start audio stream
            self.stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                stream_callback=self.audio_callback
            )
            
            self.stream.start_stream()
            self.is_recording = True
            
            self.audio_status.config(text="🎤 Audio: Active", fg='#00ff00')
            print("🎤 Audio capture initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize audio: {e}")
            self.audio_status.config(text="🎤 Audio: Failed", fg='#ff6b6b')
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream."""
        
        if self.is_recording:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Check for speech activity (simple volume threshold)
            volume = np.sqrt(np.mean(audio_data**2))
            
            if volume > 500:  # Adjust threshold as needed
                self.audio_queue.put(in_data)
        
        return (in_data, pyaudio.paContinue)
    
    def process_audio_queue(self):
        """Process queued audio data for speech recognition."""
        
        # This would integrate with speech recognition
        # For now, we'll simulate with manual input
        pass
    
    def on_config_change(self, event=None):
        """Handle configuration changes."""
        
        level = self.level_var.get()
        company = self.company_var.get()
        
        print(f"🎯 Configuration changed: {level} at {company}")
        
        # Update backend configuration
        self.update_interview_config(level, company)
    
    def update_interview_config(self, level, company):
        """Update interview configuration via API."""
        
        try:
            response = requests.post(
                'http://localhost:8084/api/set-interview-level',
                json={
                    'level': level,
                    'company': company if company else None
                },
                timeout=5
            )
            
            if response.ok:
                print(f"✅ Configuration updated: {level} at {company}")
            else:
                print(f"❌ Failed to update configuration: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error updating configuration: {e}")
    
    def handle_manual_question(self, event=None):
        """Handle manually entered questions."""
        
        question = self.manual_input.get().strip()
        if not question:
            return
        
        print(f"🧪 Manual question: {question}")
        
        # Clear input
        self.manual_input.delete(0, tk.END)
        
        # Display question
        self.display_question(question)
        
        # Get AI response
        self.get_ai_response(question)
    
    def display_question(self, question):
        """Display the current question."""
        
        self.question_display.config(state=tk.NORMAL)
        self.question_display.delete(1.0, tk.END)
        self.question_display.insert(1.0, question)
        self.question_display.config(state=tk.DISABLED)
        
        self.current_question = question
    
    def get_ai_response(self, question):
        """Get AI response for the question."""
        
        def fetch_response():
            try:
                self.display_answer("🤖 Generating response...")
                
                response = requests.post(
                    'http://localhost:8084/api/ask',
                    json={
                        'question': question,
                        'context': {
                            'type': 'interview',
                            'interview_level': self.level_var.get(),
                            'target_company': self.company_var.get() if self.company_var.get() else None,
                            'platform': 'desktop'
                        }
                    },
                    timeout=30
                )
                
                if response.ok:
                    result = response.json()
                    answer = result.get('response', 'No response available')
                    self.display_answer(answer)
                    print(f"✅ AI response received ({len(answer)} chars)")
                else:
                    self.display_answer(f"❌ Error: HTTP {response.status_code}")
                    
            except Exception as e:
                error_msg = f"❌ Failed to get AI response: {e}"
                self.display_answer(error_msg)
                print(error_msg)
        
        # Run in separate thread to avoid blocking UI
        response_thread = threading.Thread(target=fetch_response, daemon=True)
        response_thread.start()
    
    def display_answer(self, answer):
        """Display AI answer with typing effect."""
        
        self.answer_display.config(state=tk.NORMAL)
        self.answer_display.delete(1.0, tk.END)
        
        # Insert answer with proper formatting
        self.answer_display.insert(1.0, answer)
        
        self.answer_display.config(state=tk.DISABLED)
        self.answer_display.see(tk.END)
        
        self.current_answer = answer
    
    def toggle_stealth_mode(self, event=None):
        """Toggle stealth mode for desktop overlay."""
        
        self.is_stealth_mode = not self.is_stealth_mode
        
        if self.is_stealth_mode:
            # Stealth mode: Make window less visible
            self.root.attributes('-alpha', 0.1)  # Nearly transparent
            self.stealth_indicator.config(text="🕵️ STEALTH", fg='#ff6b6b')
            print("🕵️ Desktop stealth mode activated")
            
            # Move window to edge of screen
            screen_width = self.root.winfo_screenwidth()
            self.root.geometry(f"600x800+{screen_width - 50}+20")
            
        else:
            # Normal mode: Full visibility
            self.root.attributes('-alpha', 0.95)
            self.stealth_indicator.config(text="👁️ VISIBLE", fg='#00ff00')
            print("👁️ Desktop normal mode activated")
            
            # Move window back to normal position
            screen_width = self.root.winfo_screenwidth()
            self.root.geometry(f"600x800+{screen_width - 620}+20")
    
    def minimize_window(self):
        """Minimize the desktop overlay."""
        self.root.iconify()
    
    def on_closing(self):
        """Handle window closing."""
        
        print("🔄 Shutting down desktop assistant...")
        
        # Stop audio capture
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        self.root.destroy()
    
    def run(self):
        """Start the desktop application."""
        
        print("🚀 Starting Desktop AI Interview Assistant...")
        print("📍 Window positioned on right side of screen")
        print("🎤 Audio monitoring active")
        print("🕵️ Ctrl+Shift+A = Toggle stealth mode")
        
        self.root.mainloop()

def main():
    """Main entry point for desktop application."""
    
    try:
        app = DesktopInterviewAssistant()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Desktop assistant interrupted by user")
    except Exception as e:
        print(f"\n❌ Desktop assistant error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
