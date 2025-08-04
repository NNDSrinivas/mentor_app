# 🤖 AI Mentor Assistant - Universal IDE Edition

A production-ready AI-powered coding assistant that provides **real-time meeting integration** and works seamlessly across **all major IDEs**.

## 🎯 Core Features

- 🎤 **Real-time Meeting Monitoring** (Zoom, Teams, Google Meet)
- 💻 **Universal IDE Integration** (VS Code, IntelliJ, PyCharm, Sublime, Vim, Emacs, etc.)
- 🔗 **Jira Task Integration** 
- 🧠 **Context-aware Code Suggestions**
- 📡 **Inter-Extension Communication**

## 🚀 Quick Start

### 1. Start the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start all services
python start_mentor_app.py
```

### 2. Install Browser Extension
1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" 
4. Select `browser_extension/` folder

### 3. Configuration
Create `.env` file from template:
```bash
cp .env.template .env
# Edit .env with your API keys
```

## 📁 Production Structure

```
mentor_app/
├── 🚀 start_mentor_app.py          # Main application launcher
├── 🌐 web_interface.py             # Flask API server
├── 🔗 universal_ide_bridge.py     # Universal IDE integration
├── 📊 check_status.py              # System status checker
├── 🛠️  setup_universal_ides.sh     # IDE setup automation
├── 
├── 🔌 browser_extension/           # Chrome extension
│   ├── manifest.json
│   ├── content.js
│   ├── background.js
│   └── popup.html
├── 
├── 💻 vscode_extension/            # VS Code extension
│   ├── package.json
│   └── src/extension.ts
├── 
└── 📱 app/                         # Core AI modules
    ├── main.py
    ├── ai_assistant.py
    ├── capture.py
    └── config.py
```

## 🎮 Usage

### Meeting Integration
1. Join any meeting platform (Zoom, Teams, Google Meet)
2. Extension automatically detects and monitors
3. AI becomes context-aware of discussions

### IDE Assistance  
1. Open any supported IDE
2. Press `Ctrl+Alt+A` for AI help
3. Get coding suggestions based on meeting context

### System Monitoring
```bash
# Check all services
python check_status.py
```

## 🔧 Supported Platforms

### IDEs
- VS Code, IntelliJ IDEA, PyCharm, WebStorm
- Sublime Text, Atom, Vim, Emacs
- Android Studio, PhpStorm

### Meeting Platforms
- Zoom, Microsoft Teams, Google Meet
- WebEx, Slack Huddles

### Programming Languages
- Python, JavaScript, TypeScript, Java
- C++, Go, Rust, PHP, Ruby, Swift

## 🛠️ Architecture

- **Web Interface** (Port 8080) - Main API and dashboard
- **Universal IDE Bridge** (Port 8081) - IDE integration hub  
- **Browser Extension** - Meeting monitoring
- **IDE Extensions** - Editor-specific integrations

## 📞 Support

### Status Check
```bash
python check_status.py
```

### Logs
Application logs in: `mentor_app.log`

### Troubleshooting
- Ensure all services are running
- Check Chrome extension is enabled
- Verify API keys in `.env` file

## 🔒 Security

- All processing happens locally
- Meeting content not stored permanently  
- Minimal browser permissions
- API keys kept secure in `.env`

## 📄 License

MIT License

---

**🚀 Ready to revolutionize your coding workflow with AI assistance across all IDEs!**
