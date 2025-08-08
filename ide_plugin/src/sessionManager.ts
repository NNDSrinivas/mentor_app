// ide_plugin/src/sessionManager.ts

import * as vscode from 'vscode';

export interface Answer {
    id: string;
    question: string;
    text: string;
    timestamp: string;
    userLevel: string;
    memoryContextUsed?: boolean;
}

export class InterviewSessionManager {
    private sessionId: string | null = null;
    private eventSource: EventSource | null = null;
    private answers: Answer[] = [];
    private currentAnswerIndex = 0;
    private statusBar: vscode.StatusBarItem;
    private context: vscode.ExtensionContext;
    private onAnswersUpdated = new vscode.EventEmitter<Answer[]>();
    
    public readonly onAnswersUpdatedEvent = this.onAnswersUpdated.event;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.setupStatusBar();
    }

    private setupStatusBar() {
        this.statusBar = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right, 
            100
        );
        this.statusBar.command = 'aiInterviewAssistant.toggle';
        this.updateStatusBar('Disconnected');
        this.statusBar.show();
        this.context.subscriptions.push(this.statusBar);
    }

    private updateStatusBar(status: string, answers?: number) {
        const answerText = answers ? ` (${answers} answers)` : '';
        this.statusBar.text = `$(mortar-board) AI Interview: ${status}${answerText}`;
    }

    async startSession(): Promise<void> {
        if (this.sessionId) {
            vscode.window.showWarningMessage('Session already active');
            return;
        }

        try {
            const config = vscode.workspace.getConfiguration('aiInterviewAssistant');
            const serverUrl = config.get<string>('serverUrl', 'http://localhost:8080');
            const userLevel = config.get<string>('userLevel', 'IC5');

            // Create session
            const response = await fetch(`${serverUrl}/api/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_level: userLevel,
                    meeting_type: 'technical_interview',
                    user_name: 'vscode_user'
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to create session: ${response.statusText}`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            // Connect to event stream
            this.connectToEventStream(serverUrl);
            
            this.updateStatusBar('Connected');
            vscode.commands.executeCommand('setContext', 'aiInterviewAssistant.sessionActive', true);
            
            const showNotifications = config.get<boolean>('showNotifications', true);
            if (showNotifications) {
                vscode.window.showInformationMessage('AI Interview Assistant session started');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`Failed to start session: ${error}`);
            this.updateStatusBar('Failed');
        }
    }

    private connectToEventStream(serverUrl: string) {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(`${serverUrl}/api/sessions/${this.sessionId}/stream`);
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (error) {
                console.error('Error parsing event data:', error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            this.updateStatusBar('Disconnected');
            
            // Attempt reconnection
            setTimeout(() => {
                if (this.sessionId) {
                    this.connectToEventStream(serverUrl);
                }
            }, 5000);
        };
    }

    private handleEvent(data: any) {
        switch (data.type) {
            case 'new_answer':
                this.addAnswer(data.data, true);
                break;
            case 'historical_answer':
                this.addAnswer(data.data, false);
                break;
            case 'session_ended':
                this.endSession();
                break;
        }
    }

    private addAnswer(answerData: any, isNew: boolean) {
        const answer: Answer = {
            id: `${this.sessionId}-${this.answers.length}`,
            question: answerData.question,
            text: answerData.answer,
            timestamp: answerData.timestamp,
            userLevel: answerData.user_level,
            memoryContextUsed: answerData.memory_context_used
        };

        this.answers.push(answer);
        
        if (isNew) {
            this.currentAnswerIndex = this.answers.length - 1;
            this.showNewAnswerNotification(answer);
        }

        this.updateStatusBar('Connected', this.answers.length);
        this.onAnswersUpdated.fire(this.answers);
    }

    private showNewAnswerNotification(answer: Answer) {
        const config = vscode.workspace.getConfiguration('aiInterviewAssistant');
        const showNotifications = config.get<boolean>('showNotifications', true);
        
        if (showNotifications) {
            const shortQuestion = answer.question.length > 50 
                ? answer.question.substring(0, 50) + '...'
                : answer.question;
                
            vscode.window.showInformationMessage(
                `New answer available: ${shortQuestion}`,
                'Show Answer'
            ).then(selection => {
                if (selection === 'Show Answer') {
                    this.showCurrentAnswer();
                }
            });
        }
    }

    async showCurrentAnswer(): Promise<void> {
        if (this.answers.length === 0) {
            vscode.window.showInformationMessage('No answers available yet');
            return;
        }

        const answer = this.answers[this.currentAnswerIndex];
        
        // Create a new document to show the answer
        const doc = await vscode.workspace.openTextDocument({
            content: this.formatAnswerForDisplay(answer),
            language: 'markdown'
        });
        
        await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    }

    private formatAnswerForDisplay(answer: Answer): string {
        return `# Interview Question

**Timestamp:** ${new Date(answer.timestamp).toLocaleString()}  
**Level:** ${answer.userLevel}  
**Context Used:** ${answer.memoryContextUsed ? 'Yes' : 'No'}

## Question
${answer.question}

## Suggested Answer
${answer.text}

---
*Generated by AI Interview Assistant*
`;
    }

    endSession(): void {
        if (!this.sessionId) {
            return;
        }

        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        this.sessionId = null;
        this.answers = [];
        this.currentAnswerIndex = 0;
        
        this.updateStatusBar('Disconnected');
        vscode.commands.executeCommand('setContext', 'aiInterviewAssistant.sessionActive', false);
        
        vscode.window.showInformationMessage('AI Interview Assistant session ended');
        this.onAnswersUpdated.fire([]);
    }

    toggleSession(): void {
        if (this.sessionId) {
            this.endSession();
        } else {
            this.startSession();
        }
    }

    getAnswers(): Answer[] {
        return this.answers;
    }

    dispose(): void {
        this.endSession();
        this.statusBar.dispose();
        this.onAnswersUpdated.dispose();
    }
}
