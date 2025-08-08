// ide_plugin/src/answerTreeProvider.ts

import * as vscode from 'vscode';
import { InterviewSessionManager, Answer } from './sessionManager';

export class AnswerTreeProvider implements vscode.TreeDataProvider<AnswerItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AnswerItem | undefined | null | void> = new vscode.EventEmitter<AnswerItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AnswerItem | undefined | null | void> = this._onDidChangeTreeData.event;

    constructor(private sessionManager: InterviewSessionManager) {
        // Listen to answer updates
        sessionManager.onAnswersUpdatedEvent(() => {
            this._onDidChangeTreeData.fire();
        });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: AnswerItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AnswerItem): Thenable<AnswerItem[]> {
        if (!element) {
            // Root level - show all answers
            const answers = this.sessionManager.getAnswers();
            return Promise.resolve(answers.map((answer, index) => 
                new AnswerItem(answer, index + 1)
            ));
        }
        
        return Promise.resolve([]);
    }
}

class AnswerItem extends vscode.TreeItem {
    constructor(
        public readonly answer: Answer,
        public readonly index: number
    ) {
        const shortQuestion = answer.question.length > 50 
            ? answer.question.substring(0, 50) + '...'
            : answer.question;
            
        super(shortQuestion, vscode.TreeItemCollapsibleState.None);
        
        this.tooltip = `${answer.question}\n\nLevel: ${answer.userLevel}\nTime: ${new Date(answer.timestamp).toLocaleTimeString()}`;
        this.description = `${answer.userLevel} • ${new Date(answer.timestamp).toLocaleTimeString()}`;
        
        // Add context indicators
        if (answer.memoryContextUsed) {
            this.iconPath = new vscode.ThemeIcon('database');
        } else {
            this.iconPath = new vscode.ThemeIcon('comment-discussion');
        }
        
        // Add context menu commands
        this.contextValue = 'answer';
        
        // Command to show full answer when clicked
        this.command = {
            command: 'aiInterviewAssistant.showAnswerDetails',
            title: 'Show Answer Details',
            arguments: [this.answer]
        };
    }
}
