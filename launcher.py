#!/usr/bin/env python3
"""
Universal AI Interview Assistant Launcher

This script detects your meeting environment and launches the appropriate assistant:
- Browser meetings → Chrome Extension
- Desktop applications → Desktop Overlay
- Universal fallback → Standalone App

Supports all major meeting platforms:
✅ Browser: Zoom Web, Teams Web, Google Meet, WebEx Web
✅ Desktop: Zoom App, Teams App, WebEx App, Skype, Discord, Slack
"""

import os
import sys
import subprocess
import psutil
import time
import requests
import tkinter as tk
from tkinter import messagebox
import webbrowser
import json

class UniversalInterviewLauncher:
    """Detects meeting environment and launches appropriate assistant."""
    
    def __init__(self):
        self.browser_meetings = [
            'zoom.us', 'teams.microsoft.com', 'meet.google.com', 
            'webex.com', 'whereby.com', 'jitsi.org'
        ]
        
        self.desktop_apps = {
            'zoom': ['zoom.exe', 'zoom', 'Zoom.app', 'ZoomOpener.exe'],
            'teams': ['Teams.exe', 'teams', 'Microsoft Teams.app'],
            'webex': ['CiscoCollabHost.exe', 'webex', 'Webex.app', 'ptoneclk.exe'],
            'skype': ['Skype.exe', 'skype', 'Skype.app'],
            'discord': ['Discord.exe', 'discord', 'Discord.app'],
            'slack': ['slack.exe', 'slack', 'Slack.app'],
            'bluejeans': ['BlueJeans.exe', 'bluejeans'],
            'gotomeeting': ['GoToMeeting.exe', 'gotomeeting']
        }
        
        self.chrome_browsers = [
            'chrome.exe', 'chrome', 'Google Chrome.app',
            'msedge.exe', 'msedge', 'Microsoft Edge.app',
            'brave.exe', 'brave', 'Brave Browser.app'
        ]
    
    def detect_environment(self):
        """Detect current meeting environment."""
        
        environment = {
            'browser_meetings': [],
            'desktop_apps': [],
            'browsers': [],
            'recommendation': 'unknown'
        }
        
        # Check for running browsers with meeting sites
        browser_meetings = self.detect_browser_meetings()
        environment['browser_meetings'] = browser_meetings
        
        # Check for desktop meeting apps
        desktop_apps = self.detect_desktop_meeting_apps()
        environment['desktop_apps'] = desktop_apps
        
        # Check for browsers (for extension deployment)
        browsers = self.detect_browsers()
        environment['browsers'] = browsers
        
        # Make recommendation
        if browser_meetings and browsers:
            environment['recommendation'] = 'browser_extension'
        elif desktop_apps:
            environment['recommendation'] = 'desktop_overlay'
        elif browsers:
            environment['recommendation'] = 'browser_extension_ready'
        else:
            environment['recommendation'] = 'standalone_app'
        
        return environment
    
    def detect_browser_meetings(self):
        """Detect browser-based meeting sessions."""
        
        detected = []
        
        try:
            # Check running processes for browsers
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if not proc.info['cmdline']:
                        continue
                    
                    cmdline = ' '.join(proc.info['cmdline']).lower()
                    
                    # Check if browser is running meeting sites
                    for meeting_site in self.browser_meetings:
                        if meeting_site in cmdline:
                            detected.append(meeting_site)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"❌ Error detecting browser meetings: {e}")
        
        return list(set(detected))  # Remove duplicates
    
    def detect_desktop_meeting_apps(self):
        """Detect desktop meeting applications."""
        
        detected = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    process_name = proc.info['name'].lower()
                    
                    for app_name, process_names in self.desktop_apps.items():
                        for proc_pattern in process_names:
                            if proc_pattern.lower() in process_name:
                                if app_name not in detected:
                                    detected.append(app_name)
                                break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"❌ Error detecting desktop apps: {e}")
        
        return detected
    
    def detect_browsers(self):
        """Detect running browsers."""
        
        detected = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    process_name = proc.info['name'].lower()
                    
                    for browser_name in self.chrome_browsers:
                        if browser_name.lower() in process_name:
                            browser_type = browser_name.split('.')[0].split(' ')[0]
                            if browser_type not in detected:
                                detected.append(browser_type)
                            break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"❌ Error detecting browsers: {e}")
        
        return detected
    
    def check_ai_service(self):
        """Check if AI service is running."""
        
        try:
            response = requests.get('http://localhost:8084/api/health', timeout=3)
            return response.ok
        except:
            return False
    
    def start_ai_service(self):
        """Start the AI service if not running."""
        
        if self.check_ai_service():
            print("✅ AI service already running")
            return True
        
        print("🚀 Starting AI service...")
        
        try:
            # Start the web interface in background
            subprocess.Popen([
                sys.executable, 'web_interface.py'
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            # Wait for service to start
            for i in range(10):
                time.sleep(1)
                if self.check_ai_service():
                    print("✅ AI service started successfully")
                    return True
                print(f"⏳ Waiting for AI service... ({i+1}/10)")
            
            print("❌ AI service failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting AI service: {e}")
            return False
    
    def install_browser_extension(self):
        """Guide user to install browser extension."""
        
        extension_path = os.path.join(os.path.dirname(__file__), 'browser_extension')
        
        instructions = f"""
🔧 BROWSER EXTENSION INSTALLATION:

1. Open Chrome/Edge browser
2. Go to: chrome://extensions/ (or edge://extensions/)
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked"
5. Select this folder: {extension_path}
6. Extension will appear with green icon
7. Join your meeting and assistant will activate automatically

✅ For browser-based meetings (Zoom Web, Teams Web, etc.)
"""
        
        return instructions
    
    def launch_desktop_overlay(self):
        """Launch desktop overlay assistant."""
        
        try:
            # Check if desktop dependencies are available
            missing_deps = self.check_desktop_dependencies()
            
            if missing_deps:
                return f"""
❌ Missing dependencies for desktop mode:
{chr(10).join(f"   pip install {dep}" for dep in missing_deps)}

Please install missing packages and try again.
"""
            
            print("🖥️ Launching desktop overlay...")
            
            subprocess.Popen([
                sys.executable, 'desktop_interview_assistant.py'
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            return "✅ Desktop overlay launched successfully!"
            
        except Exception as e:
            return f"❌ Error launching desktop overlay: {e}"
    
    def check_desktop_dependencies(self):
        """Check for desktop-specific dependencies."""
        
        required_packages = ['tkinter', 'pyaudio', 'psutil', 'numpy']
        missing = []
        
        for package in required_packages:
            try:
                if package == 'tkinter':
                    import tkinter
                elif package == 'pyaudio':
                    import pyaudio
                elif package == 'psutil':
                    import psutil
                elif package == 'numpy':
                    import numpy
            except ImportError:
                missing.append(package)
        
        return missing
    
    def launch_standalone_app(self):
        """Launch standalone web app."""
        
        try:
            # Open web interface in browser
            webbrowser.open('http://localhost:8084')
            return "✅ Standalone web app opened in browser"
            
        except Exception as e:
            return f"❌ Error launching standalone app: {e}"
    
    def create_launcher_gui(self):
        """Create GUI launcher for easy selection."""
        
        root = tk.Tk()
        root.title("🤖 AI Interview Assistant Launcher")
        root.geometry("700x600")
        root.configure(bg='#1a1a1a')
        
        # Header
        header_frame = tk.Frame(root, bg='#1a1a1a')
        header_frame.pack(fill=tk.X, pady=20)
        
        title_label = tk.Label(
            header_frame,
            text="🤖 AI Interview Assistant",
            font=('Arial', 20, 'bold'),
            fg='#00ff00',
            bg='#1a1a1a'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Universal launcher for all meeting platforms",
            font=('Arial', 12),
            fg='#888888',
            bg='#1a1a1a'
        )
        subtitle_label.pack()
        
        # Environment detection
        env_frame = tk.Frame(root, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        env_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            env_frame,
            text="🔍 Environment Detection:",
            font=('Arial', 14, 'bold'),
            fg='#00ff00',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Detect environment
        environment = self.detect_environment()
        
        # Display detected environment
        if environment['browser_meetings']:
            meetings_text = "✅ Browser meetings: " + ", ".join(environment['browser_meetings'])
            tk.Label(env_frame, text=meetings_text, font=('Courier', 10), fg='#00ff00', bg='#2a2a2a').pack(anchor=tk.W, padx=20)
        
        if environment['desktop_apps']:
            apps_text = "✅ Desktop apps: " + ", ".join(environment['desktop_apps'])
            tk.Label(env_frame, text=apps_text, font=('Courier', 10), fg='#00ff00', bg='#2a2a2a').pack(anchor=tk.W, padx=20)
        
        if environment['browsers']:
            browsers_text = "✅ Browsers: " + ", ".join(environment['browsers'])
            tk.Label(env_frame, text=browsers_text, font=('Courier', 10), fg='#888888', bg='#2a2a2a').pack(anchor=tk.W, padx=20)
        
        if not any([environment['browser_meetings'], environment['desktop_apps']]):
            tk.Label(env_frame, text="⏳ No active meetings detected", font=('Courier', 10), fg='#ff6b6b', bg='#2a2a2a').pack(anchor=tk.W, padx=20)
        
        tk.Label(env_frame, text="", bg='#2a2a2a').pack(pady=5)  # Spacer
        
        # Options frame
        options_frame = tk.Frame(root, bg='#1a1a1a')
        options_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Browser Extension Option
        browser_frame = tk.Frame(options_frame, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        browser_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            browser_frame,
            text="🌐 Browser Extension (Web Meetings)",
            font=('Arial', 12, 'bold'),
            fg='#00aaff',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Label(
            browser_frame,
            text="For: Zoom Web, Teams Web, Google Meet, WebEx Web",
            font=('Arial', 10),
            fg='#888888',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=20)
        
        browser_btn = tk.Button(
            browser_frame,
            text="📋 Show Installation Instructions",
            command=lambda: self.show_browser_instructions(),
            font=('Arial', 10),
            bg='#00aaff',
            fg='white',
            width=30
        )
        browser_btn.pack(anchor=tk.W, padx=20, pady=(5, 10))
        
        # Desktop Overlay Option
        desktop_frame = tk.Frame(options_frame, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        desktop_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            desktop_frame,
            text="🖥️ Desktop Overlay (Desktop Apps)",
            font=('Arial', 12, 'bold'),
            fg='#ff6600',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Label(
            desktop_frame,
            text="For: Zoom App, Teams App, WebEx App, Skype, Discord",
            font=('Arial', 10),
            fg='#888888',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=20)
        
        desktop_btn = tk.Button(
            desktop_frame,
            text="🚀 Launch Desktop Overlay",
            command=lambda: self.handle_desktop_launch(),
            font=('Arial', 10),
            bg='#ff6600',
            fg='white',
            width=30
        )
        desktop_btn.pack(anchor=tk.W, padx=20, pady=(5, 10))
        
        # Standalone Option
        standalone_frame = tk.Frame(options_frame, bg='#2a2a2a', relief=tk.RIDGE, bd=2)
        standalone_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            standalone_frame,
            text="🌍 Standalone Web App",
            font=('Arial', 12, 'bold'),
            fg='#00ff00',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Label(
            standalone_frame,
            text="Universal fallback - works with any platform",
            font=('Arial', 10),
            fg='#888888',
            bg='#2a2a2a'
        ).pack(anchor=tk.W, padx=20)
        
        standalone_btn = tk.Button(
            standalone_frame,
            text="🌐 Open Web App",
            command=lambda: self.handle_standalone_launch(),
            font=('Arial', 10),
            bg='#00ff00',
            fg='black',
            width=30
        )
        standalone_btn.pack(anchor=tk.W, padx=20, pady=(5, 10))
        
        # AI Service Status
        status_frame = tk.Frame(root, bg='#1a1a1a')
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ai_running = self.check_ai_service()
        status_text = "✅ AI Service: Running" if ai_running else "❌ AI Service: Stopped"
        status_color = '#00ff00' if ai_running else '#ff6b6b'
        
        self.status_label = tk.Label(
            status_frame,
            text=status_text,
            font=('Courier', 10),
            fg=status_color,
            bg='#1a1a1a'
        )
        self.status_label.pack(side=tk.LEFT)
        
        if not ai_running:
            start_service_btn = tk.Button(
                status_frame,
                text="🚀 Start AI Service",
                command=self.handle_start_service,
                font=('Arial', 9),
                bg='#ff6b6b',
                fg='white'
            )
            start_service_btn.pack(side=tk.RIGHT)
        
        # Recommendation
        recommendation_frame = tk.Frame(root, bg='#0a3a0a', relief=tk.RIDGE, bd=2)
        recommendation_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        rec_text = self.get_recommendation_text(environment)
        tk.Label(
            recommendation_frame,
            text=f"💡 Recommendation: {rec_text}",
            font=('Arial', 11, 'bold'),
            fg='#00ff00',
            bg='#0a3a0a'
        ).pack(padx=10, pady=10)
        
        root.mainloop()
    
    def get_recommendation_text(self, environment):
        """Get recommendation text based on environment."""
        
        if environment['recommendation'] == 'browser_extension':
            return "Use Browser Extension for active web meetings"
        elif environment['recommendation'] == 'desktop_overlay':
            return "Use Desktop Overlay for active desktop apps"
        elif environment['recommendation'] == 'browser_extension_ready':
            return "Install Browser Extension, then join web meeting"
        else:
            return "Use Standalone Web App as universal fallback"
    
    def show_browser_instructions(self):
        """Show browser extension installation instructions."""
        
        instructions = self.install_browser_extension()
        
        instruction_window = tk.Toplevel()
        instruction_window.title("Browser Extension Installation")
        instruction_window.geometry("600x400")
        instruction_window.configure(bg='#1a1a1a')
        
        text_widget = tk.Text(
            instruction_window,
            font=('Courier', 10),
            fg='#00ff00',
            bg='#1a1a1a',
            wrap=tk.WORD
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        text_widget.insert(1.0, instructions)
        text_widget.config(state=tk.DISABLED)
    
    def handle_desktop_launch(self):
        """Handle desktop overlay launch."""
        
        if not self.check_ai_service():
            if not self.start_ai_service():
                messagebox.showerror("Error", "Failed to start AI service")
                return
        
        result = self.launch_desktop_overlay()
        messagebox.showinfo("Desktop Overlay", result)
    
    def handle_standalone_launch(self):
        """Handle standalone app launch."""
        
        if not self.check_ai_service():
            if not self.start_ai_service():
                messagebox.showerror("Error", "Failed to start AI service")
                return
        
        result = self.launch_standalone_app()
        messagebox.showinfo("Standalone App", result)
    
    def handle_start_service(self):
        """Handle AI service start."""
        
        if self.start_ai_service():
            self.status_label.config(text="✅ AI Service: Running", fg='#00ff00')
            messagebox.showinfo("Success", "AI service started successfully!")
        else:
            messagebox.showerror("Error", "Failed to start AI service")
    
    def run_auto_launcher(self):
        """Run automatic launcher based on detected environment."""
        
        print("🔍 Detecting meeting environment...")
        environment = self.detect_environment()
        
        print(f"📊 Browser meetings: {environment['browser_meetings']}")
        print(f"🖥️ Desktop apps: {environment['desktop_apps']}")
        print(f"🌐 Browsers: {environment['browsers']}")
        print(f"💡 Recommendation: {environment['recommendation']}")
        
        # Start AI service if not running
        if not self.check_ai_service():
            print("🚀 Starting AI service...")
            if not self.start_ai_service():
                print("❌ Failed to start AI service - launching GUI")
                self.create_launcher_gui()
                return
        
        # Auto-launch based on recommendation
        if environment['recommendation'] == 'desktop_overlay':
            print("🖥️ Auto-launching desktop overlay...")
            result = self.launch_desktop_overlay()
            print(result)
        elif environment['recommendation'] == 'browser_extension':
            print("🌐 Browser meetings detected - use extension in browser")
            print(self.install_browser_extension())
        else:
            print("🚀 Launching GUI for manual selection...")
            self.create_launcher_gui()

def main():
    """Main entry point."""
    
    print("🎯 Universal AI Interview Assistant Launcher")
    print("=" * 50)
    
    launcher = UniversalInterviewLauncher()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == 'gui':
            launcher.create_launcher_gui()
        elif mode == 'desktop':
            launcher.handle_desktop_launch()
        elif mode == 'browser':
            print(launcher.install_browser_extension())
        elif mode == 'web':
            launcher.handle_standalone_launch()
        else:
            print("Usage: python launcher.py [gui|desktop|browser|web]")
    else:
        # Auto-detect and launch
        launcher.run_auto_launcher()

if __name__ == "__main__":
    main()
