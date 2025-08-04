# Universal IDE Integration System
# Works with VS Code, IntelliJ, PyCharm, WebStorm, Sublime, Atom, Vim, Emacs, etc.

import subprocess
import json
import time
import os
import psutil
import threading
from pathlib import Path
import requests
import websocket
import tempfile
from typing import Dict, List, Optional, Any

class UniversalIDEBridge:
    """Universal IDE integration that works with ANY IDE"""
    
    def __init__(self):
        self.supported_ides = {
            'vscode': {'name': 'Visual Studio Code', 'detector': self.detect_vscode},
            'intellij': {'name': 'IntelliJ IDEA', 'detector': self.detect_intellij},
            'pycharm': {'name': 'PyCharm', 'detector': self.detect_pycharm},
            'webstorm': {'name': 'WebStorm', 'detector': self.detect_webstorm},
            'sublime': {'name': 'Sublime Text', 'detector': self.detect_sublime},
            'atom': {'name': 'Atom', 'detector': self.detect_atom},
            'vim': {'name': 'Vim', 'detector': self.detect_vim},
            'emacs': {'name': 'Emacs', 'detector': self.detect_emacs},
            'phpstorm': {'name': 'PhpStorm', 'detector': self.detect_phpstorm},
            'android_studio': {'name': 'Android Studio', 'detector': self.detect_android_studio}
        }
        
        self.active_ides = {}
        self.temp_dir = Path(tempfile.gettempdir()) / 'ai_mentor_ide'
        self.temp_dir.mkdir(exist_ok=True)
        
        self.bridge_server_port = 8081
        self.start_bridge_server()
        self.start_ide_monitoring()

    def start_bridge_server(self):
        """Start local server for IDE communication"""
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        
        self.bridge_app = Flask(__name__)
        CORS(self.bridge_app)
        
        @self.bridge_app.route('/api/ide-command', methods=['POST'])
        def receive_ide_command():
            """Receive command from IDE"""
            try:
                data = request.get_json()
                command = data.get('command')
                params = data.get('params', {})
                
                response = self.execute_command(command, params)
                return jsonify(response)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.bridge_app.route('/api/status')
        def get_status():
            """Get bridge status"""
            return jsonify({
                'status': 'running',
                'active_ides': list(self.active_ides.keys()),
                'supported_ides': list(self.supported_ides.keys()),
                'message': 'Universal IDE Bridge is operational'
            })

        @self.bridge_app.route('/api/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'service': 'universal_ide_bridge'})

        @self.bridge_app.route('/')
        def index():
            """Bridge status page"""
            return f"""
            <html>
            <head><title>Universal IDE Bridge</title></head>
            <body>
                <h1>🔗 Universal IDE Bridge</h1>
                <p><strong>Status:</strong> Running</p>
                <p><strong>Active IDEs:</strong> {', '.join(self.active_ides.keys()) or 'None detected'}</p>
                <p><strong>Supported IDEs:</strong> {len(self.supported_ides)} total</p>
                <h3>API Endpoints:</h3>
                <ul>
                    <li><a href="/api/status">/api/status</a> - Status information</li>
                    <li><a href="/api/health">/api/health</a> - Health check</li>
                </ul>
            </body>
            </html>
            """        @self.bridge_app.route('/api/ide-status')
        def ide_status():
            return jsonify({
                'active_ides': list(self.active_ides.keys()),
                'supported_count': len(self.supported_ides),
                'monitoring': True
            })
        
        # Run server in background thread
        threading.Thread(
            target=lambda: self.bridge_app.run(
                host='localhost', 
                port=self.bridge_server_port, 
                debug=False
            ),
            daemon=True
        ).start()
        
        print(f"🔗 Universal IDE Bridge running on localhost:{self.bridge_server_port}")

    def start_ide_monitoring(self):
        """Continuously monitor for active IDEs"""
        def monitor():
            while True:
                self.detect_active_ides()
                time.sleep(5)  # Check every 5 seconds
        
        threading.Thread(target=monitor, daemon=True).start()
        print("👁️ IDE monitoring started")

    def detect_active_ides(self):
        """Detect which IDEs are currently running"""
        current_ides = {}
        
        for ide_key, ide_info in self.supported_ides.items():
            if ide_info['detector']():
                current_ides[ide_key] = ide_info['name']
        
        # Update active IDEs and notify of changes
        if current_ides != self.active_ides:
            newly_opened = set(current_ides.keys()) - set(self.active_ides.keys())
            newly_closed = set(self.active_ides.keys()) - set(current_ides.keys())
            
            for ide in newly_opened:
                self.on_ide_opened(ide)
            
            for ide in newly_closed:
                self.on_ide_closed(ide)
            
            self.active_ides = current_ides

    # ===========================================
    # IDE DETECTION METHODS
    # ===========================================

    def detect_vscode(self) -> bool:
        """Detect VS Code"""
        return self._process_running(['code', 'code-insiders', 'Visual Studio Code'])

    def detect_intellij(self) -> bool:
        """Detect IntelliJ IDEA"""
        return self._process_running(['idea', 'intellij', 'IntelliJ IDEA'])

    def detect_pycharm(self) -> bool:
        """Detect PyCharm"""
        return self._process_running(['pycharm', 'PyCharm'])

    def detect_webstorm(self) -> bool:
        """Detect WebStorm"""
        return self._process_running(['webstorm', 'WebStorm'])

    def detect_sublime(self) -> bool:
        """Detect Sublime Text"""
        return self._process_running(['sublime_text', 'subl', 'Sublime Text'])

    def detect_atom(self) -> bool:
        """Detect Atom"""
        return self._process_running(['atom', 'Atom'])

    def detect_vim(self) -> bool:
        """Detect Vim"""
        return self._process_running(['vim', 'nvim', 'gvim'])

    def detect_emacs(self) -> bool:
        """Detect Emacs"""
        return self._process_running(['emacs', 'Emacs'])

    def detect_phpstorm(self) -> bool:
        """Detect PhpStorm"""
        return self._process_running(['phpstorm', 'PhpStorm'])

    def detect_android_studio(self) -> bool:
        """Detect Android Studio"""
        return self._process_running(['studio', 'Android Studio'])

    def _process_running(self, process_names: List[str]) -> bool:
        """Check if any of the given process names are running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                proc_name = proc.info['name'] or ''
                proc_cmdline = ' '.join(proc.info['cmdline'] or [])
                
                for name in process_names:
                    if (name.lower() in proc_name.lower() or 
                        name.lower() in proc_cmdline.lower()):
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False

    # ===========================================
    # IDE INTEGRATION METHODS
    # ===========================================

    def on_ide_opened(self, ide_key: str):
        """Handle when an IDE is opened"""
        ide_name = self.supported_ides[ide_key]['name']
        print(f"✅ {ide_name} detected and connected")
        
        # Install AI assistant plugins/scripts for the IDE
        self.install_ai_assistant(ide_key)

    def on_ide_closed(self, ide_key: str):
        """Handle when an IDE is closed"""
        ide_name = self.supported_ides[ide_key]['name']
        print(f"❌ {ide_name} disconnected")

    def install_ai_assistant(self, ide_key: str):
        """Install AI assistant integration for specific IDE"""
        if ide_key == 'vscode':
            self.install_vscode_extension()
        elif ide_key in ['intellij', 'pycharm', 'webstorm', 'phpstorm', 'android_studio']:
            self.install_jetbrains_plugin(ide_key)
        elif ide_key == 'sublime':
            self.install_sublime_plugin()
        elif ide_key == 'vim':
            self.install_vim_plugin()
        elif ide_key == 'emacs':
            self.install_emacs_plugin()
        else:
            self.install_universal_file_watcher(ide_key)

    def install_vscode_extension(self):
        """Install VS Code extension we already created"""
        # Extension already exists - just ensure it's active
        print("🔌 VS Code extension ready")

    def install_jetbrains_plugin(self, ide_key: str):
        """Install plugin for JetBrains IDEs (IntelliJ, PyCharm, etc.)"""
        plugin_script = f"""
// AI Mentor Assistant Plugin for {ide_key}
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.fileEditor.FileEditorManager;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class AIMentorPlugin {{
    private static final String BRIDGE_URL = "http://localhost:{self.bridge_server_port}";
    
    public void sendToBridge(String action, Object data) {{
        // Send data to universal bridge
        HttpClient client = HttpClient.newHttpClient();
        // Implementation for sending HTTP requests
    }}
    
    public void onFileOpened(String filePath) {{
        sendToBridge("file_opened", Map.of("file", filePath, "ide", "{ide_key}"));
    }}
    
    public void onCodeChanged(String code) {{
        sendToBridge("code_changed", Map.of("code", code, "ide", "{ide_key}"));
    }}
}}
"""
        # Create plugin file
        plugin_path = self.temp_dir / f"{ide_key}_plugin.java"
        plugin_path.write_text(plugin_script)
        print(f"🔌 {ide_key} plugin installed at {plugin_path}")

    def install_sublime_plugin(self):
        """Install Sublime Text plugin"""
        plugin_script = """
import sublime
import sublime_plugin
import urllib.request
import json

class AiMentorListener(sublime_plugin.EventListener):
    BRIDGE_URL = "http://localhost:8081"
    
    def on_post_save_async(self, view):
        file_path = view.file_name()
        if file_path:
            self.send_to_bridge("file_saved", {"file": file_path, "ide": "sublime"})
    
    def on_selection_modified_async(self, view):
        selection = view.substr(view.sel()[0])
        if len(selection) > 10:
            self.send_to_bridge("selection_changed", {"selection": selection, "ide": "sublime"})
    
    def send_to_bridge(self, action, data):
        try:
            payload = json.dumps({"action": action, "data": data}).encode('utf-8')
            req = urllib.request.Request(f"{self.BRIDGE_URL}/api/ide-command", 
                                       data=payload, 
                                       headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"AI Mentor: {e}")

class AiMentorAskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        question = sublime.active_window().show_input_panel(
            "Ask AI Mentor:", "", self.on_question, None, None)
    
    def on_question(self, question):
        # Send question to AI bridge
        pass
"""
        plugin_path = self.temp_dir / "ai_mentor_sublime.py"
        plugin_path.write_text(plugin_script)
        print(f"🔌 Sublime Text plugin installed at {plugin_path}")

    def install_vim_plugin(self):
        """Install Vim plugin"""
        plugin_script = """
\" AI Mentor Assistant for Vim
if !exists('g:ai_mentor_loaded')
    let g:ai_mentor_loaded = 1
    
    function! AIMentorSendToBridge(action, data)
        let l:curl_cmd = 'curl -s -X POST http://localhost:8081/api/ide-command -H "Content-Type: application/json" -d "{\\"action\\": \\"' . a:action . '\\", \\"data\\": ' . json_encode(a:data) . '}"'
        call system(l:curl_cmd)
    endfunction
    
    function! AIMentorOnFileOpen()
        call AIMentorSendToBridge('file_opened', {'file': expand('%:p'), 'ide': 'vim'})
    endfunction
    
    function! AIMentorAsk()
        let l:question = input('Ask AI Mentor: ')
        if l:question != ''
            call AIMentorSendToBridge('ai_question', {'question': l:question, 'ide': 'vim'})
        endif
    endfunction
    
    " Auto-commands
    autocmd BufEnter * call AIMentorOnFileOpen()
    
    " Commands
    command! AIMentorAsk call AIMentorAsk()
    
    " Key mappings
    nnoremap <leader>ai :AIMentorAsk<CR>
endif
"""
        plugin_path = self.temp_dir / "ai_mentor.vim"
        plugin_path.write_text(plugin_script)
        print(f"🔌 Vim plugin installed at {plugin_path}")

    def install_emacs_plugin(self):
        """Install Emacs plugin"""
        plugin_script = """
;;; ai-mentor.el --- AI Mentor Assistant for Emacs

(defvar ai-mentor-bridge-url "http://localhost:8081"
  "URL for AI Mentor bridge server")

(defun ai-mentor-send-to-bridge (action data)
  "Send data to AI Mentor bridge"
  (let ((url-request-method "POST")
        (url-request-extra-headers '(("Content-Type" . "application/json")))
        (url-request-data (json-encode `((action . ,action) (data . ,data)))))
    (url-retrieve (concat ai-mentor-bridge-url "/api/ide-command") 
                  (lambda (status) nil))))

(defun ai-mentor-on-file-open ()
  "Handle file open event"
  (when buffer-file-name
    (ai-mentor-send-to-bridge "file_opened" 
                              `((file . ,buffer-file-name) (ide . "emacs")))))

(defun ai-mentor-ask ()
  "Ask AI Mentor a question"
  (interactive)
  (let ((question (read-string "Ask AI Mentor: ")))
    (when (not (string-empty-p question))
      (ai-mentor-send-to-bridge "ai_question" 
                                `((question . ,question) (ide . "emacs"))))))

;; Hooks
(add-hook 'find-file-hook 'ai-mentor-on-file-open)

;; Key bindings
(global-set-key (kbd "C-c a") 'ai-mentor-ask)

(provide 'ai-mentor)
;;; ai-mentor.el ends here
"""
        plugin_path = self.temp_dir / "ai-mentor.el"
        plugin_path.write_text(plugin_script)
        print(f"🔌 Emacs plugin installed at {plugin_path}")

    def install_universal_file_watcher(self, ide_key: str):
        """Universal file watcher for any IDE"""
        import watchdog.observers
        import watchdog.events
        
        class AIFileHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, bridge):
                self.bridge = bridge
                self.ide_key = ide_key
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(('.py', '.js', '.java', '.cpp', '.c', '.go')):
                    self.bridge.handle_file_change(event.src_path, self.ide_key)
        
        # Watch common project directories
        observer = watchdog.observers.Observer()
        handler = AIFileHandler(self)
        
        watch_dirs = [
            os.path.expanduser("~/Projects"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
        ]
        
        for watch_dir in watch_dirs:
            if os.path.exists(watch_dir):
                observer.schedule(handler, watch_dir, recursive=True)
        
        observer.start()
        print(f"📁 Universal file watcher installed for {ide_key}")

    # ===========================================
    # COMMAND HANDLING
    # ===========================================

    def handle_ide_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle commands from IDEs"""
        action = data.get('action')
        command_data = data.get('data', {})
        
        try:
            if action == 'file_opened':
                return self.handle_file_opened(command_data)
            elif action == 'code_changed':
                return self.handle_code_changed(command_data)
            elif action == 'ai_question':
                return self.handle_ai_question(command_data)
            elif action == 'file_saved':
                return self.handle_file_saved(command_data)
            elif action == 'selection_changed':
                return self.handle_selection_changed(command_data)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def handle_file_opened(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file opened in IDE"""
        file_path = data.get('file')
        ide = data.get('ide')
        
        # Send to main AI service
        self.notify_main_service('file_opened', {
            'file': file_path,
            'ide': ide,
            'timestamp': time.time()
        })
        
        return {'success': True, 'message': f'File opened: {file_path}'}

    def handle_code_changed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code changes"""
        code = data.get('code')
        ide = data.get('ide')
        
        # Analyze code for issues or provide suggestions
        suggestions = self.analyze_code(code)
        
        return {'success': True, 'suggestions': suggestions}

    def handle_ai_question(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI questions from IDE"""
        question = data.get('question')
        ide = data.get('ide')
        
        # Send to main AI service
        response = self.ask_ai_service(question, {'source': f'ide_{ide}'})
        
        return {'success': True, 'response': response}

    def handle_file_saved(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file save events"""
        file_path = data.get('file')
        ide = data.get('ide')
        
        # Trigger code analysis
        self.notify_main_service('file_saved', data)
        
        return {'success': True}

    def handle_selection_changed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle text selection changes"""
        selection = data.get('selection')
        ide = data.get('ide')
        
        # Provide context-aware help for selected code
        if len(selection) > 20:  # Only for substantial selections
            help_text = self.get_code_help(selection)
            return {'success': True, 'help': help_text}
        
        return {'success': True}

    def handle_file_change(self, file_path: str, ide_key: str):
        """Handle file change from file watcher"""
        self.notify_main_service('file_changed', {
            'file': file_path,
            'ide': ide_key,
            'timestamp': time.time()
        })

    # ===========================================
    # AI INTEGRATION
    # ===========================================

    def notify_main_service(self, action: str, data: Dict[str, Any]):
        """Send data to main AI service"""
        try:
            requests.post('http://localhost:8080/api/ide-event', json={
                'action': action,
                'data': data,
                'timestamp': time.time()
            }, timeout=1)
        except:
            pass  # Silently handle if main service is not available

    def ask_ai_service(self, question: str, context: Dict[str, Any]) -> str:
        """Ask question to main AI service"""
        try:
            response = requests.post('http://localhost:8080/api/ask', json={
                'question': question,
                'context': context
            }, timeout=10)
            
            if response.ok:
                return response.json().get('response', 'No response')
            else:
                return 'AI service unavailable'
        except:
            return 'AI service connection failed'

    def analyze_code(self, code: str) -> List[str]:
        """Analyze code and provide suggestions"""
        suggestions = []
        
        # Basic code analysis
        if 'TODO' in code.upper():
            suggestions.append('💡 Consider implementing the TODO items')
        
        if 'print(' in code and 'python' in code.lower():
            suggestions.append('🐛 Consider using logging instead of print statements')
        
        if len(code.split('\n')) > 50:
            suggestions.append('📏 Consider breaking this into smaller functions')
        
        return suggestions

    def get_code_help(self, code: str) -> str:
        """Get help for selected code"""
        return self.ask_ai_service(f"Explain this code: {code}", {'type': 'code_explanation'})

# ===========================================
# STARTUP
# ===========================================

if __name__ == "__main__":
    print("🚀 Starting Universal IDE Bridge...")
    bridge = UniversalIDEBridge()
    
    print("🎯 Supported IDEs:")
    for ide_key, ide_info in bridge.supported_ides.items():
        print(f"  • {ide_info['name']}")
    
    print("\n✅ Universal IDE Bridge ready!")
    print("📡 Monitoring for IDE activity...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Universal IDE Bridge shutting down...")
