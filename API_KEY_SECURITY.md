# 🔐 API Key Security & User Setup Guide

## 🚨 CRITICAL: API Key Security

### ✅ **What We've Done for Security:**

1. **Environment Variables Only**
   - API keys stored in `.env` file (never in code)
   - `.env` file is in `.gitignore` (won't be committed)
   - Template file (`.env.template`) safe for public repos

2. **No Hardcoded Keys**
   - All API keys loaded from environment
   - Fallback to mock mode if no key provided
   - Clear error messages guide users to setup

3. **Repository Safety**
   - `.env` excluded from git commits
   - Template shows structure without real keys
   - Setup instructions guide users properly

### ⚠️ **User Responsibilities:**

1. **Get Your Own API Key**
   - Visit https://platform.openai.com/
   - Create account and get API key
   - Add credits to your account

2. **Setup Process**
   ```bash
   # 1. Copy template
   cp .env.template .env
   
   # 2. Edit with your key
   nano .env  # Replace 'your_openai_api_key_here' with actual key
   
   # 3. Never commit .env
   git status  # Should NOT show .env file
   ```

## 📋 **For Users: Complete Setup Instructions**

### **Step 1: Get OpenAI API Key**

1. **Visit OpenAI Platform**
   - Go to https://platform.openai.com/
   - Create account or sign in

2. **Create API Key**
   - Navigate to "API Keys" section
   - Click "Create new secret key"
   - Give it a name (e.g., "AI Mentor App")
   - **Copy the key immediately** (you won't see it again!)

3. **Add Credits**
   - Go to "Billing" section
   - Add payment method
   - Add $5-10 in credits (enough for extensive testing)
   - Set usage limits if desired

### **Step 2: Configure Application**

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd mentor_app
   ```

2. **Setup Environment**
   ```bash
   # Create Python environment
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   ```bash
   # Copy environment template
   cp .env.template .env
   
   # Edit .env file (use any text editor)
   nano .env
   ```
   
   **Replace this line:**
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   
   **With your actual key:**
   ```
   OPENAI_API_KEY=sk-proj-abc123...your-actual-key-here
   ```

### **Step 3: Test Setup**

1. **Start Application**
   ```bash
   python3 simple_web_clean.py
   ```

2. **Verify in Browser**
   - Open http://localhost:8084
   - Try asking: "What is React?"
   - Should get real AI response (not mock)

### **Step 4: Browser Extension (Optional)**

1. **Install Extension**
   - Open Chrome: chrome://extensions/
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select `browser_extension/` folder

2. **Test in Meeting**
   - Join Google Meet or Zoom
   - Extension starts in stealth mode (private)
   - Use speech recognition or manual input

## 🔒 **Security Best Practices**

### **For Developers:**
- ✅ Never commit `.env` files
- ✅ Use `.env.template` for documentation
- ✅ Load keys from environment variables
- ✅ Provide fallback/mock modes
- ✅ Clear setup instructions for users

### **For Users:**
- ✅ Keep API keys private
- ✅ Set usage limits in OpenAI dashboard
- ✅ Monitor API usage regularly
- ✅ Rotate keys periodically
- ✅ Never share keys in screenshots/support

## 🧪 **Testing & Verification**

### **Verify Security Setup:**
```bash
# Check .env is ignored
git status
# Should NOT see .env in the list

# Check API key is loaded
python3 -c "from app.config import Config; print('API key loaded:', len(Config.OPENAI_API_KEY) > 10)"
```

### **Verify Functionality:**
1. **Web Interface:** Real AI responses at http://localhost:8084
2. **Browser Extension:** Works in Google Meet/Zoom
3. **Resume Upload:** Personalized responses
4. **Privacy Mode:** AI hidden from other participants

## 🆘 **Troubleshooting**

### **"Invalid API Key" Error:**
- Check your key in .env file
- Ensure you have OpenAI credits
- Verify key format (starts with sk-proj-)

### **"Mock Response" Appearing:**
- API key not loaded properly
- Check .env file location and format
- Restart the application

### **Extension Not Working:**
- Grant microphone permissions
- Check Chrome console for errors
- Reload extension

## 📊 **Cost Management**

### **OpenAI Pricing (Approximate):**
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- GPT-4: ~$0.03 per 1K tokens
- Typical question: 100-500 tokens
- **Estimated cost: $0.001-0.015 per question**

### **Usage Tips:**
- Set monthly limits in OpenAI dashboard
- Monitor usage regularly
- Use shorter questions when possible
- Consider GPT-3.5 for cost savings

---

## 🎯 **Summary for Repository Owner**

### **What's Protected:**
✅ No API keys in repository  
✅ .env files excluded from git  
✅ Clear user setup process  
✅ Fallback modes for testing  
✅ Security documentation  

### **What Users Need to Do:**
1. Get their own OpenAI API key
2. Copy .env.template to .env
3. Add their API key to .env
4. Follow setup instructions

### **Benefits of This Approach:**
- ✅ Repository safe for public use
- ✅ Each user responsible for their own keys
- ✅ Clear setup process
- ✅ No accidental key exposure
- ✅ Production-ready security model

**The application is now secure and ready for public distribution!** 🚀
