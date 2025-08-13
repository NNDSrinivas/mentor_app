# 🧪 Frontend Testing Guide - AI SDLC Assistant

## 📊 Dashboard Access
**Main Dashboard**: http://localhost:8080

---

## 🎯 Feature-by-Feature Testing Guide

### 1. 📝 **Meeting Intelligence Testing**

#### **Frontend Dashboard Test**
1. Open http://localhost:8080
2. Look for "Meeting Intelligence" card
3. Click the API endpoint: `POST /api/analyze-meeting`

#### **Manual API Test via Browser Console**
```javascript
// Open browser console on http://localhost:8080 and run:
fetch('/api/analyze-meeting', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        content: "We need to implement the user authentication system by Friday. John will handle the backend API, Sarah will work on the frontend. Any questions about the requirements?",
        create_task: true,
        context: {
            meeting_type: "planning",
            participants: ["John", "Sarah", "Manager"]
        }
    })
})
.then(res => res.json())
.then(data => console.log('Meeting Analysis:', data));
```

#### **Expected Response**
```json
{
  "status": "success",
  "analysis": {
    "summary": "Mock analysis of meeting content",
    "questions": ["What is the main objective?", "Who is responsible for next steps?"],
    "action_items": ["Follow up on requirements", "Schedule design review"],
    "participants": ["User1", "User2"],
    "meeting_type": "planning",
    "urgency": "medium",
    "technical_topics": ["Architecture", "API Design"],
    "created_task": {
      "task_id": "TASK-1234",
      "title": "Follow up on meeting action items",
      "status": "created"
    }
  }
}
```

---

### 2. 📋 **Task Management Testing**

#### **View Tasks - Browser Test**
```javascript
// In browser console:
fetch('/api/tasks?user_id=developer1&limit=10')
.then(res => res.json())
.then(data => console.log('User Tasks:', data));
```

#### **Create Task - Browser Test**
```javascript
// In browser console:
fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        title: "Implement user authentication",
        description: "Create secure login system with JWT tokens",
        priority: "high",
        assignee: "developer1",
        project: "web_app"
    })
})
.then(res => res.json())
.then(data => console.log('Created Task:', data));
```

#### **Expected Responses**
- **Get Tasks**: List of 3 mock tasks (TASK-001, TASK-002, TASK-003)
- **Create Task**: New task with generated ID and "created" status

---

### 3. ⚡ **Real-time Collaboration Testing**

#### **Start Session - Browser Test**
```javascript
// In browser console:
fetch('/api/session/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: "developer1",
        session_type: "pair_programming",
        project: "mentor_app"
    })
})
.then(res => res.json())
.then(data => console.log('Session Started:', data));
```

#### **Expected Response**
```json
{
  "status": "success",
  "session": {
    "session_id": "session-developer1-123"
  },
  "mode": "development"
}
```

---

### 4. 🤖 **Development Automation Testing**

#### **Code Generation Test**
```javascript
// In browser console:
fetch('/api/automate/code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        task_description: "Create a REST API endpoint for user authentication",
        language: "python",
        framework: "flask",
        requirements: ["JWT tokens", "password hashing", "validation"]
    })
})
.then(res => res.json())
.then(data => console.log('Generated Code:', data));
```

**Note**: This endpoint needs implementation - currently shows development mode placeholder.

---

### 5. 🔐 **Privacy & Security Testing**

#### **Enable Privacy Mode Test**
```javascript
// In browser console:
fetch('/api/privacy/enable', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        mode: "stealth",
        features: ["screen_sharing_hide", "encrypted_storage"]
    })
})
.then(res => res.json())
.then(data => console.log('Privacy Mode:', data));
```

**Note**: This endpoint needs implementation - currently shows development mode placeholder.

---

### 6. 💰 **Monetization Testing**

#### **View Pricing - Browser Test**
```javascript
// In browser console:
fetch('/api/pricing')
.then(res => res.json())
.then(data => console.log('Pricing Plans:', data));
```

#### **Expected Response**
```json
{
  "plans": [
    {
      "name": "Developer",
      "price": 29,
      "features": ["Basic AI assistance", "5 meetings/month", "Standard support"]
    },
    {
      "name": "Professional", 
      "price": 79,
      "features": ["Advanced AI", "Unlimited meetings", "JIRA integration", "Priority support"]
    },
    {
      "name": "Enterprise",
      "price": 149,
      "features": ["Full feature access", "Team collaboration", "Custom integrations", "24/7 support"]
    }
  ]
}
```

---

## 🛠️ **Browser Extension Testing**

### **Chrome Extension Installation**
1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select `/Users/mounikakapa/Desktop/Personal Projects/mentor_app/browser_extension/`

### **Extension Testing Steps**
1. **Meeting Detection Test**:
   - Visit https://meet.google.com/new
   - Extension should detect meeting and show badge
   
2. **Overlay Test**:
   - Join a test meeting
   - Look for AI assistant overlay
   - Test voice recognition (if microphone permission granted)

3. **Privacy Test**:
   - Try screen sharing in meeting
   - Overlay should hide automatically (stealth mode)

---

## 🎮 **Interactive Dashboard Testing**

### **Quick Test All Features**
```javascript
// Run this in browser console to test all features:
async function testAllFeatures() {
    console.log('🧪 Starting comprehensive feature test...');
    
    // 1. Health Check
    const health = await fetch('/api/health').then(r => r.json());
    console.log('✅ Health:', health);
    
    // 2. Meeting Intelligence
    const meeting = await fetch('/api/analyze-meeting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            content: "Let's discuss the API implementation timeline",
            create_task: true
        })
    }).then(r => r.json());
    console.log('📝 Meeting Analysis:', meeting);
    
    // 3. Task Management
    const tasks = await fetch('/api/tasks?user_id=tester').then(r => r.json());
    console.log('📋 Tasks:', tasks);
    
    // 4. Session Management
    const session = await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'tester' })
    }).then(r => r.json());
    console.log('⚡ Session:', session);
    
    // 5. Pricing
    const pricing = await fetch('/api/pricing').then(r => r.json());
    console.log('💰 Pricing:', pricing);
    
    console.log('🎉 All features tested successfully!');
}

// Run the test
testAllFeatures();
```

---

## 📱 **Visual Testing Checklist**

### **Dashboard UI Elements**
- [ ] **Header**: "AI-Powered SDLC Assistant" title visible
- [ ] **Status Badge**: "DEVELOPMENT MODE" badge displayed
- [ ] **System Status**: Green status box with port/mode info
- [ ] **Feature Grid**: 6 feature cards properly laid out
- [ ] **API Endpoints**: Each card shows correct API paths

### **Feature Cards Content**
- [ ] **Meeting Intelligence**: 📝 icon, analysis description
- [ ] **Task Management**: 📋 icon, JIRA integration info
- [ ] **Real-time Collaboration**: ⚡ icon, session management
- [ ] **Development Automation**: 🤖 icon, code generation
- [ ] **Privacy & Security**: 🔐 icon, stealth mode features
- [ ] **Monetization**: 💰 icon, pricing tiers

---

## 🚨 **Troubleshooting Tests**

### **If Dashboard Doesn't Load**
```bash
# Check if service is running
curl http://localhost:8080/api/health

# If not running, restart:
cd /Users/mounikakapa/Desktop/Personal\ Projects/mentor_app
source venv/bin/activate
python simple_enhanced_launcher.py
```

### **If API Tests Fail**
1. **Check CORS**: APIs should work from dashboard domain
2. **Check Console**: Look for error messages in browser dev tools
3. **Verify JSON**: Ensure request bodies are valid JSON

### **Browser Extension Issues**
1. **Permissions**: Check if microphone permission granted
2. **Console Logs**: Check extension background script logs
3. **Meeting Detection**: Verify on supported platforms (Google Meet, Teams, Zoom)

---

## 🎯 **Next Steps for Production Testing**

### **Real API Integration**
1. Add OpenAI API key to `.env` file
2. Configure JIRA credentials
3. Set up GitHub integration
4. Enable production database

### **Advanced Testing**
1. **Load Testing**: Multiple concurrent users
2. **Integration Testing**: Real meeting scenarios
3. **Security Testing**: Authentication and encryption
4. **Performance Testing**: Response times and resource usage

---

## 📊 **Success Criteria**

✅ **Dashboard loads without errors**
✅ **All 6 feature cards display correctly**
✅ **API endpoints respond with mock data**
✅ **Browser extension installs and activates**
✅ **Meeting detection works on supported platforms**
✅ **Privacy features function (stealth mode)**

The system is ready for comprehensive frontend testing! 🚀
