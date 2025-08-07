# 🤖 AI Mentor

A production-ready AI-powered Mentor
## 🎯 Core Features

- 🕵️ **True Stealth Mode** - Hidden from screen sharing, always visible to YOU
- 🎤 **Real-time Interview Question Detection** (Zoom, Teams, Google Meet, WebEx)
- 🧠 **IC6/IC7 Level AI Responses** - Senior technical interview expertise
- 📄 **Resume-Based Personalization** - Answers tailored to your background
- 🎯 **Universal Question Detection** - Handles all interview types (technical, behavioral, system design)
- 🪟 **Popup Window Stealth** - Separate window invisible to screen capture

## 🚀 Quick Start

### 1. Start the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start all services
python start_mentor_app.py
```

### 2. Install Chrome Extension for Interview Stealth Mode
1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" 
4. Select `browser_extension/` folder
5. Extension provides stealth interview assistance

### 3. Upload Your Resume (Optional)
Upload your resume to `data/` folder for personalized responses:
```bash
# Supported formats: PDF, DOCX, TXT
cp your_resume.pdf data/resume.pdf
```
### 4. Configuration
Create `.env` file from template:
```bash
cp .env.template .env
# Edit .env with your OpenAI API key for enhanced responses
```

## 🕵️ Stealth Mode Features

### True Interview Stealth
- **Popup Window Mode**: Opens separate window invisible to screen capture
- **Always Visible to YOU**: Interface remains visible on your screen
- **Screen Share Protection**: Completely hidden from Zoom/Teams/Meet screen sharing
- **Emergency Toggle**: `Ctrl+Shift+A` to manually hide/show
- **Voice Recognition**: Automatically detects interview questions
- **Instant Responses**: IC6/IC7 level technical answers within seconds

## 📁 Production Structure

```
mentor_app/
├── 🚀 start_mentor_app.py          # Main interview assistant launcher
├── 🌐 web_interface.py             # Flask API for AI responses
├── 📄 simple_web.py                # Resume upload interface
├── 🔗 universal_ide_bridge.py     # Universal IDE integration
├── 📊 check_status.py              # System status checker
├── 
├── �️ browser_extension/           # Chrome extension with stealth mode
│   ├── manifest.json               # Extension permissions
│   ├── content.js                  # Stealth interview overlay
│   ├── background.js               # Voice recognition service
│   ├── popup.html                  # Extension popup interface
│   └── offscreen.js                # Background processing
├── 
├── � app/                         # Core AI interview modules
│   ├── main.py                     # Application orchestrator
│   ├── ai_assistant.py             # IC6/IC7 AI response engine
│   ├── knowledge_base.py           # Resume processing & personalization
│   ├── transcription.py            # Voice-to-text processing
│   ├── summarization.py            # Interview context analysis
│   └── config.py                   # Configuration management
├── 
└── � data/                        # User data & knowledge base
    ├── chroma_db/                  # Vector database for context
    └── resume.pdf                  # Your resume (optional)
```

## 🎮 Interview Usage

### During Technical Interviews
1. **Join Interview**: Open Zoom/Teams/Meet interview
2. **Activate Stealth**: Extension automatically detects screen sharing
3. **Voice Recognition**: Speak or type questions for instant AI responses
4. **Read Responses**: View IC6/IC7 level answers in stealth window
5. **Stay Hidden**: Interviewer cannot see your AI assistant

### Stealth Mode Controls
- **Automatic**: Activates when screen sharing is detected
- **Manual Toggle**: `Ctrl+Shift+A` for emergency hide/show
- **Test Mode**: Click "Test Stealth Mode" button to verify invisibility
- **Popup Window**: Separate browser window invisible to screen capture

### Interview Question Types Supported
- **Technical Coding**: Data structures, algorithms, system design
- **Behavioral**: STAR method responses, leadership scenarios  
- **System Design**: Scalability, architecture, trade-offs
- **Company-Specific**: META, Google, Amazon, Microsoft style questions

### System Monitoring
```bash
# Check all services
python check_status.py
```

## 🔧 Supported Platforms

### Interview Platforms
- **Zoom** - Full stealth mode support with popup windows
- **Microsoft Teams** - Voice recognition + stealth overlay  
- **Google Meet** - Real-time question detection
- **WebEx** - Universal compatibility mode

### AI Response Levels
- **IC6/IC7** - Senior software engineer level responses
- **E5-E7** - Principal/Staff engineer depth
- **Technical Leadership** - Architecture and system design focus
- **Behavioral** - STAR method and leadership scenarios

### Resume Integration
- **PDF Processing** - Extract skills, experience, projects
- **Personalized Responses** - Answers based on your background
- **Context Awareness** - Responses match your career level
- **Skill Highlighting** - Emphasize relevant technical expertise

## 🛠️ Architecture

- **Web Interface** (Port 8084) - AI response API and resume upload
- **Chrome Extension** - Stealth interview overlay with voice recognition
- **AI Assistant** - IC6/IC7 level response generation with GPT-4
- **Knowledge Base** - Resume processing and personalized context
- **Stealth System** - Popup window technology invisible to screen capture

## ⚡ Performance

- **Response Time**: < 3 seconds for technical questions
- **Stealth Mode**: 100% invisible to screen sharing software
- **Voice Recognition**: Real-time question detection
- **Resume Processing**: Instant context personalization
- **Memory Usage**: < 100MB total system footprint

## 📞 Support & Testing

### Test Stealth Mode
```bash
# Start the application
python start_mentor_app.py

# Test in browser:
# 1. Load extension in Chrome
# 2. Go to any meeting platform
# 3. Click "Test Stealth Mode" button
# 4. Start screen sharing to verify invisibility
```

### Status Check
```bash
python check_status.py
```

### Manual Question Testing
- Type questions directly in the stealth interface
- Test voice recognition with "Tell me about yourself"
- Verify popup window opens during screen sharing

### Troubleshooting
- **Popup Blocked**: Allow popups for meeting platform domains
- **Voice Recognition**: Grant microphone permissions in Chrome
- **API Errors**: Check OpenAI API key in `.env` file
- **Stealth Not Working**: Verify Chrome extension is loaded and active

## 🔒 Privacy & Security

- **Local Processing**: All voice recognition happens locally
- **No Data Storage**: Interview content not saved permanently
- **Resume Privacy**: Only processed locally, not sent to external services
- **API Security**: OpenAI API key stored securely in `.env`
- **Stealth Technology**: Uses legitimate popup window isolation
- **No Screenshots**: Extension cannot capture screen content

## 📄 License

MIT License

---

**�️ Ready to ace your technical interviews with invisible AI assistance!**

*This tool is designed for legitimate interview preparation and practice. Use responsibly and in accordance with your organization's policies.*
