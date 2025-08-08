"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = __importStar(require("vscode"));
const axios_1 = __importDefault(require("axios"));
const bridgeClient_1 = require("./bridgeClient");
function activate(context) {
    console.log('🤖 AI Mentor Assistant activated');
    const aiMentor = new AIMentorProvider(context);
    const bridgeClient = new bridgeClient_1.BridgeClient('ws://localhost:8765');
    bridgeClient.connect();
    // Register commands
    const commands = [
        vscode.commands.registerCommand('aiMentor.askQuestion', () => aiMentor.askQuestion()),
        vscode.commands.registerCommand('aiMentor.analyzeCode', () => aiMentor.analyzeSelectedCode()),
        vscode.commands.registerCommand('aiMentor.getJiraTasks', () => aiMentor.fetchJiraTasks()),
        vscode.commands.registerCommand('aiMentor.generateCode', (uri) => aiMentor.generateCodeForTask(uri)),
        vscode.commands.registerCommand('aiMentor.explainError', () => aiMentor.explainError()),
        vscode.commands.registerCommand('aiMentor.showTasks', () => bridgeClient.requestTasks())
    ];
    // Register providers
    const taskProvider = new JiraTaskProvider(aiMentor);
    vscode.window.registerTreeDataProvider('aiMentorTasks', taskProvider);
    // Auto-start monitoring
    aiMentor.startCodingSessionMonitoring();
    context.subscriptions.push(...commands);
}
exports.activate = activate;
class AIMentorProvider {
    constructor(context) {
        this.currentTask = null;
        this.meetingContext = null;
        this.isPairProgramming = false;
        this.context = context;
        this.jiraClient = new JiraClient();
        this.statusBarItem = this.createStatusBar();
        this.extensionBridge = new ExtensionBridge(this);
    }
    createStatusBar() {
        const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        statusBarItem.text = "$(robot) AI Mentor";
        statusBarItem.tooltip = "AI Mentor Assistant - Ready to help!";
        statusBarItem.command = 'aiMentor.askQuestion';
        statusBarItem.show();
        return statusBarItem;
    }
    async startCodingSessionMonitoring() {
        // Monitor file changes, errors, and coding patterns
        vscode.workspace.onDidChangeTextDocument(async (event) => {
            if (event.document.languageId === 'python' ||
                event.document.languageId === 'javascript' ||
                event.document.languageId === 'typescript') {
                await this.analyzeCodeChanges(event);
                // Notify browser extension about file activity
                this.extensionBridge.notifyFileActivity({
                    file: event.document.fileName,
                    language: event.document.languageId,
                    changes: event.contentChanges.length
                });
            }
        });
        // Monitor when files are opened
        vscode.workspace.onDidOpenTextDocument(async (document) => {
            await this.onFileOpened(document);
            // Notify browser extension
            this.extensionBridge.notifyFileOpened({
                path: document.fileName,
                language: document.languageId,
                jiraTickets: this.extractJiraTicketsFromPath(document.fileName)
            });
        });
        // Monitor diagnostics (errors/warnings)
        vscode.languages.onDidChangeDiagnostics(async (event) => {
            await this.onDiagnosticsChanged(event);
        });
        this.updateStatus("🎤 Monitoring coding session");
        // Start listening for browser extension messages
        this.extensionBridge.startListening();
    }
    async analyzeCodeChanges(event) {
        // Analyze what the user is doing and provide contextual help
        const changes = event.contentChanges;
        if (changes.length === 0)
            return;
        const lastChange = changes[changes.length - 1];
        const newText = lastChange.text;
        // Check for specific patterns that might need help
        if (this.needsAIAssistance(newText, event.document)) {
            await this.provideContextualHelp(event.document, lastChange);
        }
    }
    needsAIAssistance(text, document) {
        // Check for patterns that indicate the user might need help
        const helpPatterns = [
            'TODO:', 'FIXME:', 'HACK:', '# TODO', '// TODO',
            'def ', 'function ', 'class ', 'async def',
            'try:', 'except:', 'catch', 'throw',
            'import ', 'from ', 'require(',
            'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE '
        ];
        return helpPatterns.some(pattern => text.toLowerCase().includes(pattern.toLowerCase()));
    }
    async provideContextualHelp(document, change) {
        const lineText = document.lineAt(change.range.start.line).text;
        const context = {
            type: 'coding',
            language: document.languageId,
            fileName: document.fileName,
            currentLine: lineText,
            currentTask: this.currentTask?.summary || 'No active task'
        };
        // Generate AI suggestion based on context
        const suggestion = await this.getAISuggestion(lineText, context);
        if (suggestion) {
            this.showPrivateNotification(suggestion);
        }
    }
    async onFileOpened(document) {
        if (document.languageId === 'python' ||
            document.languageId === 'javascript' ||
            document.languageId === 'typescript') {
            // Check if this file relates to current Jira task
            const fileName = document.fileName;
            if (this.currentTask && this.isRelatedToTask(fileName, this.currentTask)) {
                const context = `Working on: ${this.currentTask.summary}`;
                this.showPrivateNotification(`🎯 ${context}\\n💡 AI Mentor ready to help with this task!`);
            }
        }
    }
    async onDiagnosticsChanged(event) {
        // Auto-explain errors when they occur
        for (const uri of event.uris) {
            const diagnostics = vscode.languages.getDiagnostics(uri);
            const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);
            if (errors.length > 0) {
                const firstError = errors[0];
                await this.autoExplainError(uri, firstError);
            }
        }
    }
    async autoExplainError(uri, diagnostic) {
        const document = await vscode.workspace.openTextDocument(uri);
        const errorLine = document.lineAt(diagnostic.range.start.line);
        const context = {
            type: 'error_explanation',
            error: diagnostic.message,
            code: errorLine.text,
            language: document.languageId
        };
        const explanation = await this.getAISuggestion(`Explain this error: ${diagnostic.message}\\nCode: ${errorLine.text}`, context);
        if (explanation) {
            this.showPrivateNotification(`🐛 Error Explanation:\\n${explanation}`);
        }
    }
    async askQuestion() {
        const question = await vscode.window.showInputBox({
            prompt: 'Ask AI Mentor anything about your code or current task',
            placeHolder: 'e.g., How do I implement authentication for this API?'
        });
        if (question) {
            const context = await this.getCurrentContext();
            const response = await this.getAISuggestion(question, context);
            this.showAIResponsePanel(question, response);
        }
    }
    async analyzeSelectedCode() {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        if (selectedText) {
            const analysis = await this.getAISuggestion(`Analyze this code and suggest improvements:\\n${selectedText}`, { type: 'code_analysis', language: editor.document.languageId });
            this.showAIResponsePanel('Code Analysis', analysis);
        }
    }
    async fetchJiraTasks() {
        try {
            this.updateStatus("📋 Fetching Jira tasks...");
            const tasks = await this.jiraClient.getUserTasks();
            if (tasks.length > 0) {
                const taskItems = tasks.map(task => ({
                    label: `${task.key}: ${task.summary}`,
                    description: task.status,
                    task: task
                }));
                const selected = await vscode.window.showQuickPick(taskItems, {
                    placeHolder: 'Select a task to work on'
                });
                if (selected && selected.task) {
                    this.currentTask = selected.task;
                    this.updateStatus(`🎯 Working on: ${this.currentTask.key}`);
                    await this.generateTaskContext(this.currentTask);
                }
            }
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to fetch Jira tasks: ${error}`);
        }
    }
    async generateCodeForTask(uri) {
        if (!this.currentTask) {
            vscode.window.showWarningMessage('Please select a Jira task first');
            return;
        }
        const codePrompt = `Generate code for Jira task: ${this.currentTask.summary}\\nDescription: ${this.currentTask.description}`;
        const generatedCode = await this.getAISuggestion(codePrompt, {
            type: 'code_generation',
            task: this.currentTask
        });
        this.showAIResponsePanel(`Code for ${this.currentTask.key}`, generatedCode);
    }
    async explainError() {
        const diagnostics = vscode.languages.getDiagnostics();
        // Find the most recent error and explain it
        // Implementation for explaining current errors
    }
    async generateTaskContext(task) {
        const contextPrompt = `I'm starting work on Jira task ${task.key}: ${task.summary}. What should I consider?`;
        const context = await this.getAISuggestion(contextPrompt, {
            type: 'task_context',
            task: task
        });
        this.showPrivateNotification(`🎯 Task Context:\\n${context}`);
    }
    async getCurrentContext() {
        const editor = vscode.window.activeTextEditor;
        return {
            type: 'general_question',
            language: editor?.document.languageId || 'unknown',
            fileName: editor?.document.fileName || 'no_file',
            currentTask: this.currentTask?.summary || 'No active task',
            workspaceRoot: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || ''
        };
    }
    async getAISuggestion(prompt, context) {
        try {
            const config = vscode.workspace.getConfiguration('aiMentor');
            const serviceUrl = config.get('mentorServiceUrl', 'http://localhost:8080');
            const response = await axios_1.default.post(`${serviceUrl}/api/ask`, {
                question: prompt,
                context: context
            });
            return response.data.response;
        }
        catch (error) {
            console.error('AI Mentor error:', error);
            return 'AI Mentor is currently unavailable. Please check your connection.';
        }
    }
    showAIResponsePanel(title, content) {
        const panel = vscode.window.createWebviewPanel('aiMentorResponse', `AI Mentor: ${title}`, vscode.ViewColumn.Beside, {});
        panel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                    .response { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; }
                    h2 { color: #0066cc; }
                </style>
            </head>
            <body>
                <h2>🤖 ${title}</h2>
                <div class="response">${content.replace(/\\n/g, '<br>')}</div>
            </body>
            </html>
        `;
    }
    showPrivateNotification(message) {
        // Show as a non-intrusive notification that only the user sees
        const notification = vscode.window.setStatusBarMessage(`🤖 ${message}`, 5000);
        // Also show as information message for important suggestions
        if (message.includes('Error') || message.includes('Task Context')) {
            vscode.window.showInformationMessage(message);
        }
    }
    isRelatedToTask(fileName, task) {
        const taskKeywords = task.summary.toLowerCase().split(' ');
        const fileNameLower = fileName.toLowerCase();
        return taskKeywords.some(keyword => keyword.length > 3 && fileNameLower.includes(keyword));
    }
    updateStatus(status) {
        this.statusBarItem.text = `$(robot) ${status}`;
    }
    // Meeting integration methods
    async onMeetingContextReceived(meetingContext) {
        this.meetingContext = meetingContext;
        if (meetingContext.jiraTickets?.length > 0) {
            // Auto-fetch discussed Jira tickets
            for (const ticketKey of meetingContext.jiraTickets) {
                await this.fetchAndSetJiraTask(ticketKey);
            }
        }
        this.updateStatus(`🎤 Meeting: ${meetingContext.meetingTitle || 'Active'}`);
        this.showPrivateNotification(`🎤 Meeting context received: ${meetingContext.meetingTitle}`);
    }
    async onPairProgrammingStarted(context) {
        this.isPairProgramming = true;
        this.updateStatus("🖥️ Pair Programming Mode");
        this.showAIResponsePanel('Pair Programming Started', `🖥️ Screen sharing detected! I'm ready to help with real-time coding assistance.\n\nMeeting: ${context.meetingContext?.meetingTitle || 'Unknown'}\nParticipants: ${context.meetingContext?.participants?.join(', ') || 'Unknown'}`);
    }
    async onCodingRequestReceived(request) {
        const question = request.request;
        const context = {
            type: 'meeting_coding_request',
            meetingContext: this.meetingContext,
            isPairProgramming: this.isPairProgramming,
            currentFile: vscode.window.activeTextEditor?.document.fileName,
            currentTask: this.currentTask
        };
        // Get AI response for the coding request
        const response = await this.getAISuggestion(question, context);
        // Show response immediately
        this.showAIResponsePanel(`Coding Request from Meeting`, response);
        // If it's a specific implementation request, generate code
        if (this.isImplementationRequest(question)) {
            await this.generateCodeFromMeetingRequest(question, context);
        }
    }
    isImplementationRequest(question) {
        const implementationKeywords = [
            'implement', 'create', 'build', 'write', 'code', 'develop',
            'add function', 'create class', 'make method'
        ];
        return implementationKeywords.some(keyword => question.toLowerCase().includes(keyword));
    }
    async generateCodeFromMeetingRequest(request, context) {
        const codePrompt = `Generate code for this meeting request: "${request}"\n\nContext:\n- Meeting: ${context.meetingContext?.meetingTitle || 'Unknown'}\n- Current file: ${context.currentFile || 'None'}\n- Current task: ${context.currentTask?.summary || 'None'}`;
        const generatedCode = await this.getAISuggestion(codePrompt, {
            type: 'code_generation_from_meeting',
            ...context
        });
        // Create new file or insert into current file
        if (vscode.window.activeTextEditor) {
            const editor = vscode.window.activeTextEditor;
            const position = editor.selection.active;
            editor.edit(editBuilder => {
                editBuilder.insert(position, `\n// Generated from meeting request: ${request}\n${generatedCode}\n`);
            });
            this.showPrivateNotification('✅ Code generated and inserted from meeting request!');
        }
        else {
            // Create new file
            const document = await vscode.workspace.openTextDocument({
                content: `// Generated from meeting request: ${request}\n${generatedCode}`,
                language: 'python'
            });
            await vscode.window.showTextDocument(document);
            this.showPrivateNotification('✅ New file created with generated code!');
        }
        // Notify browser extension that code was generated
        this.extensionBridge.notifyCodeGenerated({
            request: request,
            code: generatedCode,
            file: vscode.window.activeTextEditor?.document.fileName || 'new_file.py'
        });
    }
    async fetchAndSetJiraTask(ticketKey) {
        try {
            const task = await this.jiraClient.getTask(ticketKey);
            if (task) {
                this.currentTask = task;
                this.updateStatus(`🎯 Working on: ${task.key}`);
                this.showPrivateNotification(`🎯 Auto-selected task from meeting: ${task.summary}`);
            }
        }
        catch (error) {
            console.error(`Failed to fetch Jira task ${ticketKey}:`, error);
        }
    }
    extractJiraTicketsFromPath(filePath) {
        const jiraPattern = /[A-Z]+-\d+/g;
        return filePath.match(jiraPattern) || [];
    }
}
class JiraClient {
    async getUserTasks() {
        const config = vscode.workspace.getConfiguration('aiMentor');
        const jiraUrl = config.get('jiraUrl');
        const username = config.get('jiraUsername');
        const apiToken = config.get('jiraApiToken');
        if (!jiraUrl || !username || !apiToken) {
            throw new Error('Jira configuration missing. Please configure Jira settings.');
        }
        try {
            const response = await axios_1.default.get(`${jiraUrl}/rest/api/2/search`, {
                auth: { username, password: apiToken },
                params: {
                    jql: `assignee = "${username}" AND status != "Done"`,
                    fields: 'summary,description,status,assignee,priority'
                }
            });
            return response.data.issues.map((issue) => ({
                key: issue.key,
                summary: issue.fields.summary,
                description: issue.fields.description || '',
                status: issue.fields.status.name,
                assignee: issue.fields.assignee?.displayName || username,
                priority: issue.fields.priority?.name || 'Medium'
            }));
        }
        catch (error) {
            throw new Error(`Failed to fetch Jira tasks: ${error}`);
        }
    }
    async getTask(taskKey) {
        const config = vscode.workspace.getConfiguration('aiMentor');
        const jiraUrl = config.get('jiraUrl');
        const username = config.get('jiraUsername');
        const apiToken = config.get('jiraApiToken');
        if (!jiraUrl || !username || !apiToken) {
            throw new Error('Jira configuration missing. Please configure Jira settings.');
        }
        try {
            const response = await axios_1.default.get(`${jiraUrl}/rest/api/2/issue/${taskKey}`, {
                auth: { username, password: apiToken },
                params: {
                    fields: 'summary,description,status,assignee,priority'
                }
            });
            const issue = response.data;
            return {
                key: issue.key,
                summary: issue.fields.summary,
                description: issue.fields.description || '',
                status: issue.fields.status.name,
                assignee: issue.fields.assignee?.displayName || username,
                priority: issue.fields.priority?.name || 'Medium'
            };
        }
        catch (error) {
            console.error(`Failed to fetch Jira task ${taskKey}:`, error);
            return null;
        }
    }
}
class JiraTaskProvider {
    constructor(aiMentor) {
        this.aiMentor = aiMentor;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    }
    refresh() {
        this._onDidChangeTreeData.fire();
    }
    getTreeItem(element) {
        return {
            label: `${element.key}: ${element.summary}`,
            description: element.status,
            tooltip: element.description,
            contextValue: 'jiraTask'
        };
    }
    async getChildren(element) {
        if (!element) {
            // Return root level tasks
            try {
                const jiraClient = new JiraClient();
                return await jiraClient.getUserTasks();
            }
            catch {
                return [];
            }
        }
        return [];
    }
}
class ExtensionBridge {
    constructor(aiMentor) {
        this.pollingInterval = null;
        this.aiMentor = aiMentor;
        const config = vscode.workspace.getConfiguration('aiMentor');
        this.serviceUrl = config.get('mentorServiceUrl', 'http://localhost:8080');
    }
    startListening() {
        // Poll for messages from browser extension every 2 seconds
        this.pollingInterval = setInterval(async () => {
            await this.checkForMessages();
        }, 2000);
        console.log('🔗 Extension bridge started listening for browser messages');
    }
    stopListening() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
    async checkForMessages() {
        try {
            const response = await axios_1.default.get(`${this.serviceUrl}/api/vscode-messages`);
            const messages = response.data.messages || [];
            for (const message of messages) {
                await this.handleBrowserMessage(message);
            }
        }
        catch (error) {
            // Silently handle connection errors - service might not be running
        }
    }
    async handleBrowserMessage(message) {
        switch (message.action) {
            case 'meeting_started':
                await this.aiMentor.onMeetingContextReceived(message.data);
                break;
            case 'pair_programming_started':
                await this.aiMentor.onPairProgrammingStarted(message.data);
                break;
            case 'coding_request':
                await this.aiMentor.onCodingRequestReceived(message.data);
                break;
            case 'jira_tickets_discussed':
                await this.handleJiraTicketsDiscussed(message.data);
                break;
        }
    }
    async handleJiraTicketsDiscussed(data) {
        for (const ticket of data.tickets) {
            await this.aiMentor.fetchAndSetJiraTask(ticket);
        }
    }
    async notifyFileActivity(data) {
        this.sendToBrowser('file_activity', data);
    }
    async notifyFileOpened(data) {
        this.sendToBrowser('file_opened', data);
    }
    async notifyCodeGenerated(data) {
        this.sendToBrowser('code_generated', data);
    }
    async sendToBrowser(action, data) {
        try {
            await axios_1.default.post(`${this.serviceUrl}/api/browser-message`, {
                action: action,
                data: data,
                timestamp: new Date().toISOString()
            });
        }
        catch (error) {
            console.error('Failed to send message to browser:', error);
        }
    }
}
function deactivate() {
    console.log('🤖 AI Mentor Assistant deactivated');
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map