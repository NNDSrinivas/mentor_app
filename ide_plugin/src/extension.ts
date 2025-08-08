// ide_plugin/src/extension.ts

import * as vscode from 'vscode';
import { InterviewSessionManager } from './sessionManager';
import { AnswerTreeProvider } from './answerTreeProvider';

let sessionManager: InterviewSessionManager;
let answerTreeProvider: AnswerTreeProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('AI Interview Assistant extension activated');

    // Initialize managers
    sessionManager = new InterviewSessionManager(context);
    answerTreeProvider = new AnswerTreeProvider(sessionManager);

    // Register tree data provider
    vscode.window.createTreeView('aiInterviewAssistant', {
        treeDataProvider: answerTreeProvider,
        showCollapseAll: true
    });

    // Register commands
    const commands = [
        vscode.commands.registerCommand('aiInterviewAssistant.toggle', () => {
            sessionManager.toggleSession();
        }),
        
        vscode.commands.registerCommand('aiInterviewAssistant.startSession', () => {
            sessionManager.startSession();
        }),
        
        vscode.commands.registerCommand('aiInterviewAssistant.endSession', () => {
            sessionManager.endSession();
        }),
        
        vscode.commands.registerCommand('aiInterviewAssistant.showAnswer', () => {
            sessionManager.showCurrentAnswer();
        }),

        vscode.commands.registerCommand('aiInterviewAssistant.copyAnswer', (answer) => {
            vscode.env.clipboard.writeText(answer.text);
            vscode.window.showInformationMessage('Answer copied to clipboard');
        }),

        vscode.commands.registerCommand('aiInterviewAssistant.insertAnswer', (answer) => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.active, answer.text);
                });
            }
        })
    ];

    // Register all commands for disposal
    commands.forEach(disposable => context.subscriptions.push(disposable));

    // Auto-start if configured
    const config = vscode.workspace.getConfiguration('aiInterviewAssistant');
    if (config.get('autoStart')) {
        sessionManager.startSession();
    }

    // Set context for views
    vscode.commands.executeCommand('setContext', 'aiInterviewAssistant.sessionActive', false);
}

export function deactivate() {
    if (sessionManager) {
        sessionManager.dispose();
    }
}
