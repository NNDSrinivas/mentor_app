# 🌐 Browser Extension Testing Guide

## 📦 Installation Steps

### 1. **Load Extension in Chrome**
```bash
# Open Chrome and navigate to:
chrome://extensions/

# Enable Developer Mode (toggle in top right)
# Click "Load unpacked"
# Select folder: /Users/mounikakapa/Desktop/Personal Projects/mentor_app/browser_extension/
```

### 2. **Grant Permissions**
- **Microphone**: Required for speech recognition
- **All Sites**: Required for meeting platform integration
- **Background Scripts**: Required for meeting detection

---

## 🧪 **Step-by-Step Testing**

### **Test 1: Extension Installation**
1. ✅ Extension icon appears in Chrome toolbar
2. ✅ No error messages in extension popup
3. ✅ Extension badge shows "AI" or similar identifier

### **Test 2: Meeting Detection**
1. **Google Meet Test**:
   ```
   Visit: https://meet.google.com/new
   Expected: Extension detects meeting URL
   Result: Badge may change to "REC" or show activity
   ```

2. **Teams Test**:
   ```
   Visit: https://teams.microsoft.com (any meeting URL)
   Expected: Extension activates
   ```

3. **Zoom Test**:
   ```
   Visit: https://zoom.us/j/123456789
   Expected: Extension detects Zoom meeting
   ```

### **Test 3: Content Script Injection**
1. **Open Browser Console**: F12 → Console tab
2. **Look for Extension Logs**:
   ```
   Expected messages:
   🤖 AI Interview Assistant Loading...
   🔧 Initializing AI Interview Assistant...
   ✅ AI Interview Assistant fully initialized
   ```

3. **Check for Overlay**:
   ```
   Expected: AI assistant overlay appears on meeting pages
   Location: Usually top-right corner of screen
   ```

### **Test 4: Speech Recognition**
1. **Grant Microphone Permission** when prompted
2. **Speak into microphone**: "Hello, this is a test"
3. **Check Console Logs**:
   ```
   Expected messages:
   🎤 Voice recognition started
   👂 Listening for questions...
   🎤 Processing speech: "Hello, this is a test"
   ```

### **Test 5: AI Assistant Interaction**
1. **Ask a Question**: "What is React?"
2. **Check Response**:
   ```
   Expected: Overlay shows AI-generated answer
   Response time: Should be < 3 seconds
   ```

3. **Test Question Detection**:
   ```
   Try questions like:
   - "How do I implement authentication?"
   - "What's the best way to handle state management?"
   - "Can you explain async/await?"
   ```

### **Test 6: Privacy Features**
1. **Start Screen Sharing** in the meeting
2. **Expected Behavior**: 
   ```
   ✅ Overlay automatically hides
   ✅ Extension goes into stealth mode
   ✅ No visible AI assistant elements
   ```

3. **Stop Screen Sharing**:
   ```
   ✅ Overlay reappears
   ✅ Normal functionality resumes
   ```

### **Test 7: Hotkey Controls**
1. **Press Ctrl+Shift+H**:
   ```
   Expected: Manual stealth mode toggle
   Result: Overlay hides/shows
   ```

2. **Test in Meeting Context**:
   ```
   During active meeting:
   - Ctrl+Shift+H → Hide assistant
   - Ctrl+Shift+H → Show assistant
   ```

---

## 🔍 **Debugging & Troubleshooting**

### **Extension Console Debugging**
```bash
# To debug extension background script:
1. Go to chrome://extensions/
2. Find "AI Interview Assistant"
3. Click "Inspect views: background script"
4. Check console for errors/logs
```

### **Content Script Debugging**
```bash
# To debug content scripts:
1. Open meeting page (meet.google.com)
2. Press F12 to open DevTools
3. Go to Console tab
4. Look for AI Assistant messages
```

### **Common Issues & Fixes**

#### **Issue: Extension Not Loading**
```bash
Solution:
1. Check Chrome version (should be recent)
2. Verify manifest.json syntax
3. Reload extension in chrome://extensions/
```

#### **Issue: No Microphone Access**
```bash
Solution:
1. Check Chrome site permissions
2. Visit chrome://settings/content/microphone
3. Ensure meeting site has microphone access
```

#### **Issue: No AI Responses**
```bash
Solution:
1. Check backend service is running (localhost:8080)
2. Verify API endpoints respond
3. Check network requests in DevTools
```

#### **Issue: Overlay Not Appearing**
```bash
Solution:
1. Check console for JavaScript errors
2. Verify content script injection
3. Test on supported meeting platforms
```

---

## 📊 **Feature Verification Checklist**

### **Core Functionality**
- [ ] Extension installs without errors
- [ ] Meeting detection works on Google Meet
- [ ] Microphone permission granted
- [ ] Speech recognition activates
- [ ] AI responses generated
- [ ] Overlay displays correctly

### **Privacy Features**
- [ ] Screen sharing detection works
- [ ] Stealth mode activates automatically
- [ ] Manual stealth toggle (Ctrl+Shift+H)
- [ ] Overlay hides during screen sharing
- [ ] Privacy controls accessible

### **Integration Features**
- [ ] Backend API communication
- [ ] Real-time transcription
- [ ] Question/answer processing
- [ ] Meeting context awareness
- [ ] Multi-platform support

### **Performance**
- [ ] Response time < 3 seconds
- [ ] No memory leaks
- [ ] Smooth overlay animations
- [ ] Minimal CPU usage
- [ ] Stable during long meetings

---

## 🚀 **Advanced Testing Scenarios**

### **Real Meeting Test**
1. **Join actual Google Meet**
2. **Have conversation with colleague**
3. **Ask technical questions**
4. **Verify AI responses are contextual**

### **Multi-Speaker Test**
1. **Meeting with multiple participants**
2. **Test speaker identification**
3. **Verify question detection from different speakers**

### **Extended Session Test**
1. **Long meeting (30+ minutes)**
2. **Test memory usage stability**
3. **Verify continuous operation**

---

## 📈 **Success Metrics**

✅ **Installation Success Rate**: Extension loads without errors
✅ **Detection Accuracy**: Correctly identifies 90%+ of meeting platforms
✅ **Response Quality**: AI provides relevant, helpful answers
✅ **Privacy Compliance**: Stealth features work as expected
✅ **Performance**: <3s response time, stable operation

The browser extension is ready for comprehensive testing across all supported meeting platforms! 🎯
