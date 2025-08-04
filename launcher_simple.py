#!/usr/bin/env python3
"""
Simple AI Interview Assistant Launcher (No GUI)

This script detects your meeting environment and provides instructions:
- Browser meetings → Chrome Extension setup
- Desktop applications → Desktop overlay launch
- Universal fallback → Web interface

Works without GUI dependencies for maximum compatibility.
"""

import os
import sys
import subprocess
import psutil
import time
import requests
import webbrowser

class SimpleInterviewLauncher:
    """Simple launcher without GUI dependencies."""
    
    def __init__(self):
        self.browser_meetings = [
            'zoom.us', 'teams.microsoft.com', 'meet.google.com', 
            'webex.com', 'whereby.com', 'jitsi.org'
        ]
        
        self.desktop_apps = {
            'zoom': ['zoom.exe', 'zoom', 'Zoom.app', 'ZoomOpener.exe'],
            'teams': ['Teams.exe', 'teams', 'Microsoft Teams.app'],
            'webex': ['CiscoCollabHost.exe', 'webex', 'Webex.app'],
            'skype': ['Skype.exe', 'skype', 'Skype.app'],
            'discord': ['Discord.exe', 'discord', 'Discord.app'],
            'slack': ['slack.exe', 'slack', 'Slack.app']
        }
        
        self.chrome_browsers = [
            'chrome.exe', 'chrome', 'Google Chrome.app',
            'msedge.exe', 'msedge', 'Microsoft Edge.app'
        ]
    
    def detect_environment(self):
        """Detect current meeting environment."""
        
        environment = {
            'browser_meetings': [],
            'desktop_apps': [],
            'browsers': [],
            'recommendation': 'unknown'
        }
        
        # Check for desktop meeting apps
        desktop_apps = self.detect_desktop_meeting_apps()
        environment['desktop_apps'] = desktop_apps
        
        # Check for browsers
        browsers = self.detect_browsers()
        environment['browsers'] = browsers
        
        # Make recommendation
        if desktop_apps:
            environment['recommendation'] = 'desktop_overlay'
        elif browsers:
            environment['recommendation'] = 'browser_extension'
        else:
            environment['recommendation'] = 'standalone_app'
        
        return environment
    
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
    
    def get_browser_extension_instructions(self):
        """Get browser extension installation instructions."""
        
        extension_path = os.path.join(os.path.dirname(__file__), 'browser_extension')
        
        return f"""
🌐 BROWSER EXTENSION SETUP (For Web Meetings):

1. Open Chrome or Edge browser
2. Go to: chrome://extensions/ (or edge://extensions/)
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked" button
5. Select folder: {extension_path}
6. Extension will appear with 🤖 icon

✅ USAGE:
- Join meeting in browser (Zoom Web, Teams Web, Google Meet, etc.)
- Extension automatically activates with green overlay
- Configure interview level and company in overlay
- Ask questions verbally or type manually
- AI responses appear in stealth overlay (hidden from screen sharing)

🕵️ STEALTH FEATURES:
- Completely invisible during screen sharing
- Uses Chrome's offscreen API
- Emergency hide: Ctrl+Shift+A
"""
    
    def launch_desktop_overlay(self):
        """Launch desktop overlay assistant."""
        
        try:
            print("🖥️ Launching desktop overlay...")
            
            subprocess.Popen([
                sys.executable, 'desktop_interview_assistant.py'
            ], cwd=os.path.dirname(os.path.abspath(__file__)))
            
            return "✅ Desktop overlay launched! Check right side of screen."
            
        except Exception as e:
            return f"❌ Error launching desktop overlay: {e}"
    
    def launch_web_app(self):
        """Launch standalone web app."""
        
        try:
            # Open web interface in browser
            webbrowser.open('http://localhost:8084')
            return "✅ Web app opened at http://localhost:8084"
            
        except Exception as e:
            return f"❌ Error launching web app: {e}"
    
    def print_environment_status(self, environment):
        """Print current environment status."""
        
        print("\n" + "="*60)
        print("🔍 ENVIRONMENT DETECTION")
        print("="*60)
        
        if environment['desktop_apps']:
            print(f"✅ Desktop meeting apps detected: {', '.join(environment['desktop_apps'])}")
        else:
            print("❌ No desktop meeting apps detected")
        
        if environment['browsers']:
            print(f"✅ Browsers running: {', '.join(environment['browsers'])}")
        else:
            print("❌ No supported browsers detected")
        
        # AI Service status
        ai_running = self.check_ai_service()
        if ai_running:
            print("✅ AI service: Running")
        else:
            print("❌ AI service: Stopped")
        
        print("\n" + "="*60)
        print("💡 RECOMMENDATION")
        print("="*60)
        
        if environment['recommendation'] == 'desktop_overlay':
            print("🖥️ Use DESKTOP OVERLAY - Desktop meeting apps detected")
        elif environment['recommendation'] == 'browser_extension':
            print("🌐 Use BROWSER EXTENSION - For web meetings")
        else:
            print("🌍 Use WEB APP - Universal fallback")
    
    def run_interactive_menu(self):
        """Run interactive command-line menu."""
        
        while True:
            print("\n" + "="*60)
            print("🤖 AI INTERVIEW ASSISTANT LAUNCHER")
            print("="*60)
            print("1. 🖥️  Desktop Overlay (for Zoom App, Teams App, etc.)")
            print("2. 🌐 Browser Extension Setup (for web meetings)")
            print("3. 🌍 Web App (universal fallback)")
            print("4. 🔍 Environment Detection")
            print("5. 🚀 Start AI Service")
            print("6. ❌ Exit")
            print("="*60)
            
            try:
                choice = input("Select option (1-6): ").strip()
                
                if choice == '1':
                    if not self.check_ai_service():
                        if not self.start_ai_service():
                            print("❌ Failed to start AI service")
                            continue
                    
                    result = self.launch_desktop_overlay()
                    print(result)
                    
                elif choice == '2':
                    print(self.get_browser_extension_instructions())
                    
                elif choice == '3':
                    if not self.check_ai_service():
                        if not self.start_ai_service():
                            print("❌ Failed to start AI service")
                            continue
                    
                    result = self.launch_web_app()
                    print(result)
                    
                elif choice == '4':
                    environment = self.detect_environment()
                    self.print_environment_status(environment)
                    
                elif choice == '5':
                    self.start_ai_service()
                    
                elif choice == '6':
                    print("👋 Goodbye!")
                    break
                    
                else:
                    print("❌ Invalid choice. Please select 1-6.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def run_auto_launcher(self):
        """Run automatic launcher based on detected environment."""
        
        print("🎯 AI Interview Assistant - Universal Launcher")
        print("="*60)
        
        environment = self.detect_environment()
        self.print_environment_status(environment)
        
        # Start AI service if not running
        if not self.check_ai_service():
            if not self.start_ai_service():
                print("\n❌ Could not start AI service automatically")
                print("🔧 Running interactive menu for manual setup...")
                self.run_interactive_menu()
                return
        
        print("\n" + "="*60)
        print("🚀 AUTO-LAUNCH")
        print("="*60)
        
        # Auto-launch based on recommendation
        if environment['recommendation'] == 'desktop_overlay':
            print("🖥️ Auto-launching desktop overlay for detected meeting apps...")
            result = self.launch_desktop_overlay()
            print(result)
            
        elif environment['recommendation'] == 'browser_extension':
            print("🌐 Browser detected - showing extension setup instructions:")
            print(self.get_browser_extension_instructions())
            
        else:
            print("🌍 No specific environment detected - launching web app...")
            result = self.launch_web_app()
            print(result)
        
        print("\n💡 For more options, run: python launcher_simple.py menu")

def main():
    """Main entry point."""
    
    launcher = SimpleInterviewLauncher()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == 'menu':
            launcher.run_interactive_menu()
        elif mode == 'desktop':
            if not launcher.check_ai_service():
                launcher.start_ai_service()
            result = launcher.launch_desktop_overlay()
            print(result)
        elif mode == 'browser':
            print(launcher.get_browser_extension_instructions())
        elif mode == 'web':
            if not launcher.check_ai_service():
                launcher.start_ai_service()
            result = launcher.launch_web_app()
            print(result)
        elif mode == 'status':
            environment = launcher.detect_environment()
            launcher.print_environment_status(environment)
        else:
            print("Usage: python launcher_simple.py [menu|desktop|browser|web|status]")
    else:
        # Auto-detect and launch
        launcher.run_auto_launcher()

if __name__ == "__main__":
    main()
