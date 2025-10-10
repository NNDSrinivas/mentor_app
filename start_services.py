#!/usr/bin/env python3
"""
Clean startup script for AI Mentor services
Starts only the necessary services in the correct order
"""

import os
import sys
import time
import subprocess
import signal
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service definitions
SERVICES = {
    "knowledge": {
        "script": "start_knowledge_service.py",
        "port": 8085,
        "description": "FastAPI Knowledge Service"
    },
    "backend": {
        "script": "production_backend.py", 
        "port": 8084,
        "description": "Flask Q&A Service"
    },
    "realtime": {
        "script": "production_realtime.py",
        "port": 8080, 
        "description": "Real-time Session Service"
    }
}

class ServiceManager:
    def __init__(self):
        self.processes = {}
        self.project_root = Path(__file__).parent
        self.python_exe = self.project_root / ".venv" / "bin" / "python"
        
        # Check if virtual environment exists
        if not self.python_exe.exists():
            logger.error(f"Virtual environment not found at {self.python_exe}")
            sys.exit(1)
    
    def kill_existing_processes(self):
        """Kill any existing processes on our ports"""
        for service_name, config in SERVICES.items():
            port = config["port"]
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], 
                    capture_output=True, 
                    text=True
                )
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            logger.info(f"Killing existing process {pid} on port {port}")
                            subprocess.run(["kill", "-9", pid], check=False)
            except Exception as e:
                logger.debug(f"No existing process on port {port}: {e}")
    
    def start_service(self, service_name: str):
        """Start a single service"""
        config = SERVICES[service_name]
        script_path = self.project_root / config["script"]
        
        if not script_path.exists():
            logger.error(f"Service script not found: {script_path}")
            return False
        
        logger.info(f"Starting {config['description']} on port {config['port']}")
        
        try:
            process = subprocess.Popen(
                [str(self.python_exe), str(script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            self.processes[service_name] = process
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if it's still running
            if process.poll() is None:
                logger.info(f"✅ {config['description']} started successfully")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {config['description']} failed to start")
                logger.error(f"stdout: {stdout.decode()}")
                logger.error(f"stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return False
    
    def start_all_services(self):
        """Start all services in the correct order"""
        logger.info("🚀 Starting AI Mentor services...")
        
        # Kill any existing processes first
        self.kill_existing_processes()
        time.sleep(1)
        
        # Start services in dependency order
        service_order = ["knowledge", "backend", "realtime"]
        
        for service_name in service_order:
            if not self.start_service(service_name):
                logger.error(f"Failed to start {service_name}, stopping...")
                self.stop_all_services()
                return False
            
            # Wait between services to avoid port conflicts
            time.sleep(1)
        
        logger.info("🎉 All services started successfully!")
        self.print_status()
        return True
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info("🛑 Stopping all services...")
        
        for service_name, process in self.processes.items():
            try:
                # Kill the process group to ensure all children are killed
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                logger.info(f"✅ Stopped {service_name}")
            except Exception as e:
                logger.warning(f"Error stopping {service_name}: {e}")
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    pass
        
        self.processes.clear()
    
    def print_status(self):
        """Print service status"""
        logger.info("\n📊 Service Status:")
        for service_name, config in SERVICES.items():
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    logger.info(f"  ✅ {config['description']}: http://localhost:{config['port']}")
                else:
                    logger.info(f"  ❌ {config['description']}: Failed")
            else:
                logger.info(f"  ⏸️  {config['description']}: Not started")
        
        logger.info("\n🌐 API Endpoints:")
        logger.info("  • Q&A API: http://localhost:8084/api/ask")
        logger.info("  • Resume API: http://localhost:8084/api/resume") 
        logger.info("  • Knowledge API: http://localhost:8085/docs")
        logger.info("  • Real-time Events: http://localhost:8080/api/sessions")
    
    def monitor_services(self):
        """Monitor running services"""
        logger.info("👀 Monitoring services... (Ctrl+C to stop)")
        
        try:
            while True:
                time.sleep(10)
                
                # Check if any service died
                for service_name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.error(f"💀 Service {service_name} died unexpectedly")
                        # Optionally restart
                        del self.processes[service_name]
                        
        except KeyboardInterrupt:
            logger.info("\n📡 Received interrupt signal")
            self.stop_all_services()

def main():
    """Main entry point"""
    manager = ServiceManager()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"\n📡 Received signal {signum}")
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if manager.start_all_services():
            manager.monitor_services()
        else:
            logger.error("❌ Failed to start services")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        manager.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()
