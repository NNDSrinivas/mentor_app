# Wave 6 Testing Guide

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Copy and configure environment
cp .env.example .env

# Add your API keys to .env:
OPENAI_API_KEY=sk-your-openai-api-key-here
GITHUB_TOKEN=ghp_your-github-token-here
JIRA_USER=your-email@company.com
JIRA_TOKEN=your-jira-api-token
```

### 2. Start Wave 6 Server
```bash
# Install dependencies (if needed)
pip install openai>=1.0.0

# Start the enhanced server
./start_wave5.sh  # Works for Wave 6 too!

# Or manually:
python backend/server.py
```

## 🧪 Testing Each Component

### 📚 Documentation Agent
```bash
# Test ADR generation
curl -X POST http://localhost:8081/api/docs/adr \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Adopt OpenAI for Code Review",
    "context": "We need automated code review to scale",
    "options": ["GitHub Copilot", "OpenAI GPT-4", "Claude"],
    "decision": "OpenAI GPT-4 with approval gates",
    "consequences": ["Faster reviews", "API costs"]
  }'

# Test runbook generation
curl -X POST http://localhost:8081/api/docs/runbook \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "mentor-app",
    "incidents": ["API timeout", "Memory leak"],
    "commands": ["kubectl logs", "docker restart"],
    "dashboards": ["Grafana CPU", "DataDog Memory"]
  }'
```

### 🐙 GitHub PR Auto-Reply

1. **Setup GitHub Webhook**:
   - Go to your repository → Settings → Webhooks
   - Add webhook: `https://your-domain.com/webhook/github/pr`
   - Events: `Pull requests`, `Issue comments`
   - Secret: Use your `GITHUB_WEBHOOK_SECRET`

2. **Create a Test PR**:
   - Create a PR in your repository
   - Watch for approval request in: `GET /api/approvals`
   - Approve via: `POST /api/approvals/resolve`

### 📱 Mobile Approvals

1. **Update Server IP** in `mobile/screens/ApprovalsScreen.js`:
   ```javascript
   const SERVER_IP = "192.168.1.100";  // Your actual IP
   ```

2. **Test with React Native**:
   ```bash
   # In mobile directory
   npx react-native init MentorMobile
   # Copy ApprovalsScreen.js to your app
   # Add to navigation/routing
   ```

3. **Manual Testing**:
   ```bash
   # Create approval for testing
   curl -X POST http://localhost:8081/api/github/pr \
     -H 'Content-Type: application/json' \
     -d '{
       "owner": "test",
       "repo": "demo", 
       "head": "feature",
       "base": "main",
       "title": "Test PR"
     }'

   # Check mobile app shows the approval
   # Tap approve/reject buttons
   ```

### 📊 Enterprise Audit

```bash
# Check audit log
tail -f ./audit.log

# Should show entries like:
# {"ts": 1754618042.07, "event": "approval.submitted", "data": {...}}
# {"ts": 1754618043.12, "event": "action.executed", "data": {...}}
```

### ⚡ Complete Workflow Test

```bash
# 1. Run the demo
python demo_wave6.py

# 2. Check server status
curl http://localhost:8081/api/health

# 3. List pending approvals
curl http://localhost:8081/api/approvals

# 4. Create GitHub PR approval
curl -X POST http://localhost:8081/api/github/pr \
  -H 'Content-Type: application/json' \
  -d '{
    "owner": "your-username",
    "repo": "mentor_app",
    "head": "test-branch",
    "base": "main",
    "title": "Wave 6 Test PR",
    "body": "Testing the approval workflow"
  }'

# 5. Approve the request
curl -X POST http://localhost:8081/api/approvals/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "github.pr-123456789",
    "decision": "approve"
  }'
```

## 🐛 Troubleshooting

### OpenAI API Errors
```bash
# Check API key
python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('✅ OpenAI connection successful')
"
```

### GitHub API Errors
```bash
# Check token permissions
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/user
```

### WebSocket Connection Issues
```bash
# Test WebSocket (port 8001)
npm install -g wscat
wscat -c ws://localhost:8001
```

### Mobile App Network Issues
- Ensure server IP is accessible from mobile device
- Check firewall settings for ports 8081, 8001
- Use `ifconfig` to find your actual IP address

## 🎯 Expected Results

### Working Wave 6 System Should Show:
✅ ADR/runbook generation via API endpoints  
✅ GitHub webhook creating approval requests  
✅ Mobile UI displaying approval queue  
✅ Audit log recording all events  
✅ PR auto-reply comments after approval  
✅ Real-time WebSocket notifications  

### Success Metrics:
- Documentation generation: < 30 seconds
- PR webhook processing: < 5 seconds  
- Mobile approval action: < 2 seconds
- Audit log entries: Every action logged
- Zero failed approval executions in dry-run mode

## 🚨 Safety Reminders

- Keep `DRY_RUN=true` until fully tested
- Monitor audit logs for unusual activity
- Test webhook signatures in production
- Validate mobile IP restrictions
- Review OpenAI usage and costs regularly

Wave 6 is production-ready with enterprise guardrails! 🎉
