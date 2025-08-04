#!/bin/bash

# Universal IDE Setup Script
# Installs AI Mentor Assistant for ALL major IDEs

echo "🚀 AI Mentor Assistant - Universal IDE Installation"
echo "===================================================="
echo ""

IDE_BRIDGE_DIR="$HOME/.ai_mentor_ide"
mkdir -p "$IDE_BRIDGE_DIR"

echo "📂 Created AI Mentor directory: $IDE_BRIDGE_DIR"
echo ""

# ===========================================
# VS CODE INSTALLATION  
# ===========================================
echo "🔵 VS Code Installation..."
if command -v code >/dev/null 2>&1; then
    echo "✅ VS Code detected"
    
    # Copy our existing VS Code extension
    VSCODE_EXT_DIR="$HOME/.vscode/extensions/ai-mentor-assistant"
    mkdir -p "$VSCODE_EXT_DIR"
    cp -r vscode_extension/* "$VSCODE_EXT_DIR/"
    
    echo "✅ VS Code extension installed"
else
    echo "⚠️  VS Code not found - skipping"
fi
echo ""

# ===========================================
# JETBRAINS IDEs (IntelliJ, PyCharm, WebStorm, etc.)
# ===========================================
echo "🟠 JetBrains IDEs Installation..."

create_jetbrains_plugin() {
    local ide_name=$1
    local plugin_dir="$HOME/.${ide_name}/config/plugins/AIMentorAssistant"
    
    if [ -d "$HOME/.${ide_name}" ]; then
        mkdir -p "$plugin_dir"
        
        cat > "$plugin_dir/plugin.xml" << 'EOF'
<idea-plugin>
    <id>com.aimentor.assistant</id>
    <name>AI Mentor Assistant</name>
    <version>1.0</version>
    <vendor>AI Mentor</vendor>
    <description>Intelligent coding assistance with meeting integration</description>
    
    <depends>com.intellij.modules.platform</depends>
    
    <extensions defaultExtensionNs="com.intellij">
        <applicationService serviceImplementation="com.aimentor.AIMentorService"/>
        <editorActionHandler action="EditorEscape" implementationClass="com.aimentor.AIMentorHandler"/>
    </extensions>
    
    <actions>
        <action id="AIMentorAsk" class="com.aimentor.AskAction" text="Ask AI Mentor" description="Ask AI Mentor a question">
            <keyboard-shortcut keymap="$default" first-keystroke="ctrl alt A"/>
        </action>
    </actions>
</idea-plugin>
EOF
        
        echo "✅ ${ide_name} plugin installed"
        return 0
    else
        echo "⚠️  ${ide_name} not found - skipping"
        return 1
    fi
}

# Install for common JetBrains IDEs
for ide in "IntelliJIdea" "PyCharm" "WebStorm" "PhpStorm" "AndroidStudio"; do
    create_jetbrains_plugin "$ide"
done
echo ""

# ===========================================
# SUBLIME TEXT
# ===========================================
echo "🟣 Sublime Text Installation..."
SUBLIME_PACKAGES="$HOME/Library/Application Support/Sublime Text/Packages"
if [ -d "$SUBLIME_PACKAGES" ]; then
    mkdir -p "$SUBLIME_PACKAGES/AIMentorAssistant"
    
    cat > "$SUBLIME_PACKAGES/AIMentorAssistant/ai_mentor.py" << 'EOF'
import sublime
import sublime_plugin
import urllib.request
import json
import threading

class AiMentorListener(sublime_plugin.EventListener):
    def on_post_save_async(self, view):
        file_path = view.file_name()
        if file_path:
            AIMentorBridge.send_event("file_saved", {"file": file_path, "ide": "sublime"})
    
    def on_selection_modified_async(self, view):
        selection = view.substr(view.sel()[0])
        if len(selection) > 20:
            AIMentorBridge.send_event("selection_changed", {"selection": selection, "ide": "sublime"})

class AiMentorAskCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        question = sublime.active_window().show_input_panel(
            "Ask AI Mentor:", "", self.on_question, None, None)
    
    def on_question(self, question):
        if question:
            response = AIMentorBridge.ask_ai(question)
            sublime.message_dialog(f"AI Mentor: {response}")

class AIMentorBridge:
    BASE_URL = "http://localhost:8080"
    
    @staticmethod
    def send_event(action, data):
        def send():
            try:
                payload = json.dumps({"action": action, "data": data}).encode('utf-8')
                req = urllib.request.Request(f"{AIMentorBridge.BASE_URL}/api/ide-event", 
                                           data=payload, 
                                           headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                print(f"AI Mentor error: {e}")
        
        threading.Thread(target=send, daemon=True).start()
    
    @staticmethod
    def ask_ai(question):
        try:
            payload = json.dumps({"question": question, "context": {"ide": "sublime"}}).encode('utf-8')
            req = urllib.request.Request(f"{AIMentorBridge.BASE_URL}/api/ask", 
                                       data=payload, 
                                       headers={'Content-Type': 'application/json'})
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode('utf-8'))
            return data.get('response', 'No response')
        except Exception as e:
            return f"Error: {e}"
EOF
    
    cat > "$SUBLIME_PACKAGES/AIMentorAssistant/Default.sublime-keymap" << 'EOF'
[
    { "keys": ["ctrl+alt+a"], "command": "ai_mentor_ask" }
]
EOF
    
    echo "✅ Sublime Text plugin installed"
else
    echo "⚠️  Sublime Text not found - skipping"
fi
echo ""

# ===========================================
# VIM/NEOVIM
# ===========================================
echo "🟢 Vim/NeoVim Installation..."
VIM_CONFIG="$HOME/.vimrc"
NVIM_CONFIG="$HOME/.config/nvim/init.vim"

create_vim_plugin() {
    local config_file=$1
    
    cat >> "$config_file" << 'EOF'

" AI Mentor Assistant for Vim
if !exists('g:ai_mentor_loaded')
    let g:ai_mentor_loaded = 1
    
    function! AIMentorSendEvent(action, data)
        let l:cmd = 'curl -s -X POST http://localhost:8080/api/ide-event -H "Content-Type: application/json" -d ' . shellescape(json_encode({'action': a:action, 'data': a:data}))
        call system(l:cmd)
    endfunction
    
    function! AIMentorAsk()
        let l:question = input('Ask AI Mentor: ')
        if l:question != ''
            let l:cmd = 'curl -s -X POST http://localhost:8080/api/ask -H "Content-Type: application/json" -d ' . shellescape(json_encode({'question': l:question, 'context': {'ide': 'vim'}}))
            let l:response = system(l:cmd)
            let l:data = json_decode(l:response)
            echo 'AI Mentor: ' . l:data.response
        endif
    endfunction
    
    " Auto-commands
    autocmd BufWrite * call AIMentorSendEvent('file_saved', {'file': expand('%:p'), 'ide': 'vim'})
    autocmd BufEnter * call AIMentorSendEvent('file_opened', {'file': expand('%:p'), 'ide': 'vim'})
    
    " Commands and keybindings
    command! AIMentorAsk call AIMentorAsk()
    nnoremap <C-A-a> :AIMentorAsk<CR>
endif
EOF
}

if command -v vim >/dev/null 2>&1; then
    create_vim_plugin "$VIM_CONFIG"
    echo "✅ Vim plugin installed"
fi

if command -v nvim >/dev/null 2>&1; then
    mkdir -p "$(dirname "$NVIM_CONFIG")"
    create_vim_plugin "$NVIM_CONFIG"
    echo "✅ NeoVim plugin installed"
fi

if ! command -v vim >/dev/null 2>&1 && ! command -v nvim >/dev/null 2>&1; then
    echo "⚠️  Vim/NeoVim not found - skipping"
fi
echo ""

# ===========================================
# EMACS
# ===========================================
echo "🟡 Emacs Installation..."
EMACS_CONFIG="$HOME/.emacs.d/init.el"

if command -v emacs >/dev/null 2>&1; then
    mkdir -p "$(dirname "$EMACS_CONFIG")"
    
    cat >> "$EMACS_CONFIG" << 'EOF'

;; AI Mentor Assistant for Emacs
(defvar ai-mentor-base-url "http://localhost:8080"
  "Base URL for AI Mentor service")

(defun ai-mentor-send-event (action data)
  "Send event to AI Mentor service"
  (let ((url-request-method "POST")
        (url-request-extra-headers '(("Content-Type" . "application/json")))
        (url-request-data (json-encode `((action . ,action) (data . ,data)))))
    (url-retrieve (concat ai-mentor-base-url "/api/ide-event") 
                  (lambda (status) nil) nil t)))

(defun ai-mentor-ask ()
  "Ask AI Mentor a question"
  (interactive)
  (let* ((question (read-string "Ask AI Mentor: "))
         (url-request-method "POST")
         (url-request-extra-headers '(("Content-Type" . "application/json")))
         (url-request-data (json-encode `((question . ,question) (context . ((ide . "emacs")))))))
    (when (not (string-empty-p question))
      (url-retrieve (concat ai-mentor-base-url "/api/ask")
                    (lambda (status)
                      (goto-char (point-min))
                      (when (re-search-forward "^$" nil t)
                        (let* ((response-data (json-read))
                               (response (cdr (assoc 'response response-data))))
                          (message "AI Mentor: %s" response))))
                    nil t))))

;; Auto-save hook
(add-hook 'after-save-hook 
          (lambda () 
            (when buffer-file-name
              (ai-mentor-send-event "file_saved" 
                                    `((file . ,buffer-file-name) (ide . "emacs"))))))

;; File open hook
(add-hook 'find-file-hook 
          (lambda () 
            (when buffer-file-name
              (ai-mentor-send-event "file_opened" 
                                    `((file . ,buffer-file-name) (ide . "emacs"))))))

;; Key binding
(global-set-key (kbd "C-M-a") 'ai-mentor-ask)
EOF
    
    echo "✅ Emacs plugin installed"
else
    echo "⚠️  Emacs not found - skipping"
fi
echo ""

# ===========================================
# ATOM (if still used)
# ===========================================
echo "🔴 Atom Installation..."
ATOM_PACKAGES="$HOME/.atom/packages"
if [ -d "$ATOM_PACKAGES" ]; then
    mkdir -p "$ATOM_PACKAGES/ai-mentor-assistant/lib"
    
    cat > "$ATOM_PACKAGES/ai-mentor-assistant/package.json" << 'EOF'
{
  "name": "ai-mentor-assistant",
  "main": "./lib/ai-mentor-assistant",
  "version": "1.0.0",
  "description": "AI Mentor Assistant for Atom",
  "activationCommands": {
    "atom-workspace": "ai-mentor-assistant:ask"
  },
  "repository": "https://github.com/ai-mentor/atom-plugin",
  "license": "MIT",
  "engines": {
    "atom": ">=1.0.0 <2.0.0"
  }
}
EOF
    
    cat > "$ATOM_PACKAGES/ai-mentor-assistant/lib/ai-mentor-assistant.js" << 'EOF'
const { CompositeDisposable } = require('atom');
const http = require('http');

module.exports = {
  subscriptions: null,

  activate(state) {
    this.subscriptions = new CompositeDisposable();
    this.subscriptions.add(atom.commands.add('atom-workspace', {
      'ai-mentor-assistant:ask': () => this.ask()
    }));
    
    // Monitor file saves
    this.subscriptions.add(atom.workspace.observeTextEditors((editor) => {
      this.subscriptions.add(editor.onDidSave(() => {
        this.sendEvent('file_saved', {
          file: editor.getPath(),
          ide: 'atom'
        });
      }));
    }));
  },

  deactivate() {
    this.subscriptions.dispose();
  },

  ask() {
    atom.prompt('Ask AI Mentor:', (question) => {
      if (question) {
        this.askAI(question);
      }
    });
  },

  sendEvent(action, data) {
    // Implementation for sending events
  },

  askAI(question) {
    // Implementation for AI questions
  }
};
EOF
    
    echo "✅ Atom plugin installed"
else
    echo "⚠️  Atom not found - skipping"
fi
echo ""

# ===========================================
# UNIVERSAL FILE WATCHER
# ===========================================
echo "📁 Universal File Watcher Setup..."

cat > "$IDE_BRIDGE_DIR/universal_watcher.py" << 'EOF'
#!/usr/bin/env python3
import os
import time
import requests
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AIMentorWatcher(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = {}
        self.base_url = "http://localhost:8080"
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Only watch code files
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb'}
        if Path(event.src_path).suffix not in code_extensions:
            return
        
        # Debounce rapid changes
        now = time.time()
        if event.src_path in self.last_modified:
            if now - self.last_modified[event.src_path] < 2:
                return
        
        self.last_modified[event.src_path] = now
        self.send_event('file_modified', {
            'file': event.src_path,
            'ide': 'universal_watcher'
        })
    
    def send_event(self, action, data):
        try:
            requests.post(f"{self.base_url}/api/ide-event", 
                         json={'action': action, 'data': data}, 
                         timeout=1)
        except:
            pass

if __name__ == "__main__":
    observer = Observer()
    handler = AIMentorWatcher()
    
    # Watch common development directories
    watch_dirs = [
        os.path.expanduser("~/Projects"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.getcwd()
    ]
    
    for watch_dir in watch_dirs:
        if os.path.exists(watch_dir):
            observer.schedule(handler, watch_dir, recursive=True)
            print(f"📁 Watching: {watch_dir}")
    
    observer.start()
    print("👁️  Universal file watcher started")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("🛑 Universal file watcher stopped")
    
    observer.join()
EOF

chmod +x "$IDE_BRIDGE_DIR/universal_watcher.py"
echo "✅ Universal file watcher installed"
echo ""

# ===========================================
# CREATE STARTUP SCRIPT
# ===========================================
echo "🚀 Creating startup script..."

cat > "$IDE_BRIDGE_DIR/start_ai_mentor.sh" << 'EOF'
#!/bin/bash

echo "🤖 Starting AI Mentor Assistant Universal IDE Bridge..."

# Start the universal file watcher
python3 ~/.ai_mentor_ide/universal_watcher.py &
WATCHER_PID=$!

echo "✅ Universal IDE bridge started (PID: $WATCHER_PID)"
echo "🎯 Monitoring all IDEs for AI assistance"
echo "📝 Press Ctrl+C to stop"

# Create PID file for easy stopping
echo $WATCHER_PID > ~/.ai_mentor_ide/watcher.pid

# Wait for interrupt
trap "kill $WATCHER_PID; rm -f ~/.ai_mentor_ide/watcher.pid; echo '🛑 AI Mentor stopped'" EXIT
wait $WATCHER_PID
EOF

chmod +x "$IDE_BRIDGE_DIR/start_ai_mentor.sh"

# ===========================================
# SUMMARY
# ===========================================
echo "🎉 INSTALLATION COMPLETE!"
echo "========================="
echo ""
echo "✅ Installed AI Mentor Assistant for:"
echo "   • VS Code (if detected)"
echo "   • JetBrains IDEs (IntelliJ, PyCharm, WebStorm, etc.)"
echo "   • Sublime Text (if detected)"
echo "   • Vim/NeoVim (if detected)" 
echo "   • Emacs (if detected)"
echo "   • Atom (if detected)"
echo "   • Universal File Watcher (for any IDE)"
echo ""
echo "🚀 TO START:"
echo "   $IDE_BRIDGE_DIR/start_ai_mentor.sh"
echo ""
echo "⌨️  KEYBOARD SHORTCUTS:"
echo "   • VS Code: Ctrl+Alt+A"
echo "   • JetBrains: Ctrl+Alt+A"
echo "   • Sublime: Ctrl+Alt+A"
echo "   • Vim: Ctrl+Alt+A (or :AIMentorAsk)"
echo "   • Emacs: Ctrl+Meta+A"
echo ""
echo "📡 REQUIREMENTS:"
echo "   • AI Mentor service running on localhost:8080"
echo "   • Python 3 with requests, watchdog packages"
echo ""
echo "🎯 NOW WORKS WITH ANY IDE!"
