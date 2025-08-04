#!/usr/bin/env python3
"""
AI Mentor Application - Universal Startup Script
Enhanced with universal IDE integration for all development environments
"""

import os
import sys
import subprocess
import threading
import time
import logging
import signal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mentor_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MentorAppLauncher:
    def __init__(self):
        self.processes = []
        self.running = False
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Check for virtual environment
        venv_python = os.path.join(self.base_dir, '.venv', 'bin', 'python')
        if os.path.exists(venv_python):
            self.python_exec = venv_python
            logger.info("Using virtual environment Python")
        else:
            self.python_exec = sys.executable
            logger.info("Using system Python")
        
    def start_web_interface(self):
        """Start the Flask web interface"""
        try:
            logger.info("Starting web interface...")
            web_process = subprocess.Popen([
                self.python_exec, 
                os.path.join(self.base_dir, 'web_interface.py')
            ])
            self.processes.append(('web_interface', web_process))
            logger.info("Web interface started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            return False
    
    def start_universal_ide_bridge(self):
        """Start the universal IDE bridge"""
        try:
            logger.info("Starting universal IDE bridge...")
            bridge_process = subprocess.Popen([
                self.python_exec, 
                os.path.join(self.base_dir, 'universal_ide_bridge.py')
            ])
            self.processes.append(('ide_bridge', bridge_process))
            logger.info("Universal IDE bridge started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start IDE bridge: {e}")
            return False
    
    def check_browser_extension(self):
        """Check if browser extension is available"""
        try:
            logger.info("Checking browser extension availability...")
            extension_dir = os.path.join(self.base_dir, 'browser_extension')
            manifest_path = os.path.join(extension_dir, 'manifest.json')
            
            if os.path.exists(manifest_path):
                logger.info("✅ Browser extension found")
                return True
            else:
                logger.warning("❌ Browser extension not found")
                return False
        except Exception as e:
            logger.error(f"Error checking browser extension: {e}")
            return False
    
    def setup_vscode_extension(self):
        """Setup VS Code extension"""
        try:
            logger.info("Checking VS Code extension...")
            extension_dir = os.path.join(self.base_dir, 'vscode_extension')
            
            # Check if VS Code is available
            result = subprocess.run(['code', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.info("VS Code not found - extension not installed")
                return False
            
            logger.info("✅ VS Code found - extension ready")
            return True
                
        except Exception as e:
            logger.error(f"Error checking VS Code extension: {e}")
            return False
    
    def run_setup_script(self):
        """Run the universal IDE setup script"""
        try:
            logger.info("Running universal IDE setup...")
            setup_script = os.path.join(self.base_dir, 'setup_universal_ides.sh')
            
            if os.path.exists(setup_script):
                # Make script executable
                os.chmod(setup_script, 0o755)
                
                # Run setup script
                result = subprocess.run(['bash', setup_script], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ Universal IDE setup completed")
                    return True
                else:
                    logger.warning(f"Setup script warnings: {result.stderr}")
                    return True  # Continue even with warnings
            else:
                logger.warning("Setup script not found")
                return False
                
        except Exception as e:
            logger.error(f"Error running setup script: {e}")
            return False
    
    def display_status(self, services_started, web_port=None):
        """Display application status and instructions"""
        logger.info("=" * 60)
        logger.info("🚀 AI MENTOR APPLICATION - UNIVERSAL IDE EDITION")
        logger.info("=" * 60)
        logger.info(f"✅ {services_started} core services running")
        logger.info("")
        logger.info("📍 ACCESS POINTS:")
        if web_port:
            logger.info(f"   🌐 Web Interface: http://localhost:{web_port}")
            logger.info(f"   🔗 API Endpoint: http://localhost:{web_port}/api")
        else:
            logger.info("   🌐 Web Interface: Starting...")
        logger.info("   🛠️  IDE Bridge: Universal IDE integration active")
        logger.info("")
        logger.info("🔧 SUPPORTED IDEs:")
        logger.info("   • VS Code (with extension)")
        logger.info("   • JetBrains IDEs (IntelliJ, PyCharm, WebStorm)")
        logger.info("   • Sublime Text")
        logger.info("   • Vim/Neovim")
        logger.info("   • Emacs")
        logger.info("   • Atom")
        logger.info("   • And more...")
        logger.info("")
        logger.info("📖 SETUP INSTRUCTIONS:")
        logger.info("   1. Install browser extension from 'browser_extension/' folder")
        logger.info("   2. Open any supported IDE")
        logger.info("   3. Join a meeting (Zoom, Teams, Google Meet)")
        logger.info("   4. Use Ctrl+Alt+A for AI assistance in any IDE")
        logger.info("")
        logger.info("🎯 FEATURES:")
        logger.info("   • Real-time meeting monitoring")
        logger.info("   • Universal IDE integration")
        logger.info("   • Jira-based coding assistance")
        logger.info("   • Smart code suggestions")
        logger.info("   • Meeting context awareness")
        logger.info("=" * 60)
    
    def start_all_services(self):
        """Start all mentor app services"""
        logger.info("Initializing AI Mentor Application...")
        
        self.running = True
        services_started = 0
        
        # Run universal IDE setup
        if self.run_setup_script():
            services_started += 1
        
        # Start web interface
        if self.start_web_interface():
            services_started += 1
            time.sleep(2)  # Wait for service to initialize
        
        # Start universal IDE bridge
        if self.start_universal_ide_bridge():
            services_started += 1
            time.sleep(2)
        
        # Check browser extension
        if self.check_browser_extension():
            services_started += 1
        
        # Setup VS Code extension
        if self.setup_vscode_extension():
            services_started += 1
        
        # Display status
        self.display_status(services_started)
        
        # Wait a moment for web interface to start and detect its port
        time.sleep(3)
        
        # Try to detect web interface port
        web_port = self.detect_web_port()
        if web_port:
            logger.info(f"🌐 Web interface detected on port {web_port}")
        
        return services_started > 2  # Need at least web interface and IDE bridge
    
    def detect_web_port(self):
        """Detect which port the web interface is using"""
        import requests
        for port in range(8080, 8090):
            try:
                response = requests.get(f'http://localhost:{port}/api/health', timeout=1)
                if response.status_code == 200:
                    return port
            except:
                continue
        return None
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info("Stopping all services...")
        self.running = False
        
        for name, process in self.processes:
            try:
                logger.info(f"Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {name}...")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("All services stopped")
    
    def monitor_services(self):
        """Monitor running services"""
        grace_period = 5  # Give services 5 seconds to start properly
        time.sleep(grace_period)
        
        while self.running:
            try:
                # Check if processes are still running
                active_processes = []
                for name, process in self.processes:
                    if process.poll() is None:
                        active_processes.append((name, process))
                    else:
                        logger.warning(f"Process {name} has stopped (exit code: {process.returncode})")
                        
                        # Try to restart critical services
                        if name == 'web_interface':
                            logger.info("Attempting to restart web interface...")
                            if self.start_web_interface():
                                logger.info("Web interface restarted successfully")
                        elif name == 'ide_bridge':
                            logger.info("Attempting to restart IDE bridge...")
                            if self.start_universal_ide_bridge():
                                logger.info("IDE bridge restarted successfully")
                
                self.processes = active_processes
                
                # Check if we have minimum required services
                service_names = [name for name, _ in active_processes]
                has_web = 'web_interface' in service_names
                has_bridge = 'ide_bridge' in service_names
                
                if not (has_web and has_bridge) and self.running:
                    logger.error("Critical services missing - attempting restart...")
                    if not has_web:
                        self.start_web_interface()
                    if not has_bridge:
                        self.start_universal_ide_bridge()
                    
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error monitoring services: {e}")
                time.sleep(5)  # Wait before retrying

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info("Received termination signal")
    global app_launcher
    if app_launcher:
        app_launcher.stop_all_services()
    sys.exit(0)

def main():
    """Main application entry point"""
    global app_launcher
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app_launcher = MentorAppLauncher()
    
    try:
        # Start all services
        if app_launcher.start_all_services():
            # Monitor services
            monitor_thread = threading.Thread(target=app_launcher.monitor_services)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            logger.info("🎉 Application ready! Press Ctrl+C to stop")
            
            # Keep main thread alive
            try:
                monitor_thread.join()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
        else:
            logger.error("❌ Failed to start critical services")
            return 1
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    finally:
        app_launcher.stop_all_services()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
