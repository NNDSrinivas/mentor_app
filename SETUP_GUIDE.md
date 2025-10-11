# 🚀 AI Interview Assistant - Complete Setup Guide

## 📋 Overview

This AI Interview Assistant works with **BOTH** browser-based and desktop meeting applications:

### ✅ **Browser Meetings** (Chrome Extension)
- Zoom Web (`zoom.us`)
- Microsoft Teams Web (`teams.microsoft.com`) 
- Google Meet (`meet.google.com`)
- WebEx Web (`webex.com`)
- Any browser-based meeting platform

### ✅ **Desktop Applications** (Desktop Overlay)
- Zoom Desktop App
- Microsoft Teams Desktop App
- WebEx Desktop App
- Skype Desktop App
- Discord Desktop App
- Slack Desktop App
- Any desktop meeting application

---

## 🛠️ Installation

### 1. **Clone and Setup**
```bash
git clone <repository-url>
cd mentor_app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Environment Configuration**
Create `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
HUGGINGFACE_TOKEN=your_hf_token_here  # Optional, for speaker diarization
```

### 3. **Test Installation**
```bash
python launcher.py
```

---

## 🎯 Usage Instructions

### **Option 1: Auto-Detection (Recommended)**
```bash
python launcher.py
```
- Automatically detects your meeting environment
- Launches appropriate assistant (browser extension guide or desktop overlay)
- Starts AI service if needed

### **Option 2: Manual Selection**
```bash
python launcher.py gui
```
- Opens GUI launcher with all options
- Shows detected meeting apps and browsers
- Manual selection of assistant type

### **Option 3: Direct Launch**
```bash
# Desktop overlay for desktop apps
python launcher.py desktop

# Browser extension instructions
python launcher.py browser

# Standalone web app
python launcher.py web
```

---

## 🌐 **Browser Meetings Setup**

### **For Zoom Web, Teams Web, Google Meet, etc.**

1. **Install Chrome Extension:**
   ```bash
   python launcher.py browser
   ```
   
2. **Follow Installation Instructions:**
   - Open Chrome browser
   - Go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `browser_extension` folder
   - Extension icon will appear in toolbar

3. **Join Meeting:**
   - Join your meeting in browser
   - Extension automatically activates
   - Green overlay appears in top-right corner
   - Configure interview level and company
   - Ask questions verbally or type manually

### **Browser Extension Features:**
- ✅ **Completely stealth** - Hidden from screen sharing
- ✅ **Real-time voice recognition**
- ✅ **Company-specific responses** (Meta, Google, Amazon, etc.)
- ✅ **IC5-IC7/E5-E7 level calibration**
- ✅ **Offscreen API** for true invisibility

---

## 🖥️ **Desktop Applications Setup**

### **For Zoom App, Teams App, WebEx App, etc.**

1. **Launch Desktop Overlay:**
   ```bash
   python launcher.py desktop
   ```

2. **Automatic Detection:**
   - Assistant detects running meeting apps
   - Shows list of detected applications
   - Positions overlay on right side of screen

3. **Configure and Use:**
   - Set interview level (IC5-IC7, E5-E7)
   - Select target company
   - Type questions manually or use voice input
   - AI responses appear in overlay window

### **Desktop Overlay Features:**
- ✅ **Works with ANY desktop meeting app**
- ✅ **Always-on-top overlay window**
- ✅ **Stealth mode** (Ctrl+Shift+A to hide)
- ✅ **Audio capture** for voice questions
- ✅ **Meeting app detection**
- ✅ **Company-specific coaching**

---

## 🤖 **AI Features**

### **Resume Context Integration**
- Upload resume via web interface: `http://localhost:8084`
- Automatic skill extraction and experience mapping
- Profile-aware responses using your background
- IC6+ level calibration based on experience

### **Company-Specific Knowledge**
- **Meta**: Focus on impact, moving fast, behavioral depth
- **Google**: Algorithmic thinking, Googleyness, technical excellence  
- **Amazon**: Leadership Principles, customer obsession, ownership
- **Microsoft**: Growth mindset, collaboration, inclusive culture
- **Apple**: Innovation, excellence, product focus
- **Netflix**: High performance culture, freedom & responsibility

### **Speaker Diarization** (Advanced)
- Real-time speaker identification
- Question/answer flow detection
- Interview timing analysis
- Requires: `pip install pyannote.audio` + HuggingFace token

---

## 🔧 **Troubleshooting**

### **Common Issues:**

**❌ "AI Service not running"**
```bash
python web_interface.py
# Or use launcher to auto-start
```

**❌ "Popup blocked" (Desktop mode)**
- Allow popups for the meeting site
- Use stealth mode: Ctrl+Shift+A

**❌ "Audio not working" (Desktop mode)**
```bash
# Install audio dependencies
pip install pyaudio
# On macOS: brew install portaudio
# On Ubuntu: sudo apt-get install python3-pyaudio
```

**❌ "Extension not loading"**
- Enable Developer mode in Chrome
- Check extension folder path
- Reload extension after changes

**❌ "Dependencies missing"**
```bash
pip install -r requirements.txt
# For speaker diarization:
pip install pyannote.audio torch torchaudio
```

### **Platform-Specific Notes:**

**🍎 macOS:**
- Audio permissions may be required
- System Preferences → Security & Privacy → Microphone
- Allow Terminal/Python to access microphone

**🪟 Windows:**
- May need Visual C++ Build Tools for some packages
- Use Windows Subsystem for Linux (WSL) if issues persist

**🐧 Linux:**
- Install system audio libraries:
  ```bash
  sudo apt-get install python3-pyaudio portaudio19-dev
  ```

---

## 📊 **Testing**

### **Test Browser Extension:**
1. Load extension in Chrome
2. Go to `zoom.us` or `meet.google.com`
3. Extension should activate automatically
4. Test with sample question: "Tell me about yourself"

### **Test Desktop Overlay:**
1. Open Zoom/Teams desktop app
2. Run: `python launcher.py desktop`
3. Overlay should appear on right side
4. Test with manual input field

### **Test AI Service:**
```bash
curl http://localhost:8084/api/health
# Should return: {"status": "healthy"}
```

---

## 🎉 **Success Criteria**

You'll know it's working when:

### **Browser Mode:**
- ✅ Extension icon visible in Chrome toolbar
- ✅ Green overlay appears in meeting
- ✅ Voice recognition responds to questions
- ✅ AI provides company-specific answers
- ✅ Completely hidden during screen sharing

### **Desktop Mode:**
- ✅ Overlay window opens on right side
- ✅ Meeting apps detected and listed
- ✅ Manual questions get AI responses
- ✅ Stealth mode hides window (Ctrl+Shift+A)
- ✅ Works regardless of meeting platform

---

## 🚀 **Advanced Usage**

### **Context Window Configuration:**
Control how the AI assistant filters meeting segments for context:
```bash
# Default: Use strict boundary (>) for precise time-based filtering
CONTEXT_WINDOW_INCLUSIVE=false

# Backward compatibility: Use inclusive boundary (>=) 
CONTEXT_WINDOW_INCLUSIVE=true
```
- `false` (default): Excludes segments ending exactly at the time threshold
- `true`: Includes segments ending exactly at the time threshold (legacy behavior)

### **Custom Company Patterns:**
```python
# Add custom interview patterns via API
curl -X POST http://localhost:8084/api/add-custom-pattern \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "type": "behavioral", "pattern": "..."}'
```

### **Profile Management:**
- Upload resume: `http://localhost:8084`
- Set interview level via API or UI
- View profile context in responses

### **Speaker Diarization:**
- Set `HUGGINGFACE_TOKEN` environment variable
- Install: `pip install pyannote.audio`
- Automatic speaker identification in browser mode

---

## 📞 **Support**

**Quick Start Issues:**
1. Run `python launcher.py gui` for guided setup
2. Check `http://localhost:8084/api/health`
3. Verify all dependencies installed

**Feature Requests:**
- Browser extension supports all Chromium browsers
- Desktop overlay works with any desktop meeting app
- Web interface provides universal fallback

**Performance:**
- Response time: <2 seconds for interview responses
- Memory usage: ~200MB for full features
- Supports simultaneous browser + desktop mode

---

## 🎯 **Quick Reference**

| Meeting Type | Command | Features |
|-------------|---------|----------|
| **Zoom Web** | Browser Extension | Voice recognition, stealth mode, company-specific |
| **Teams Web** | Browser Extension | Real-time AI, invisible overlay, IC6+ responses |
| **Google Meet** | Browser Extension | Offscreen API, profile-aware answers |
| **Zoom App** | `python launcher.py desktop` | Desktop overlay, meeting detection |
| **Teams App** | `python launcher.py desktop` | Always-on-top, stealth toggle |
| **Any Platform** | `python launcher.py web` | Web interface fallback |

**Universal launcher:** `python launcher.py` (auto-detects and launches appropriate mode)

🎉 **You're now ready for AI-powered interview assistance on any platform!**
