import WebSocket from 'ws';
import * as vscode from 'vscode';

/**
 * Simple WebSocket client for communicating with the Python IDE bridge.
 */
export class BridgeClient {
    private socket: WebSocket | null = null;

    constructor(private url: string) {}

    connect() {
        this.socket = new WebSocket(this.url);

        this.socket.on('open', () => {
            console.log('🔌 Connected to IDE bridge');
        });

        this.socket.on('message', async (data: WebSocket.RawData) => {
            await this.handleMessage(data.toString());
        });

        this.socket.on('close', () => {
            console.log('❌ Disconnected from IDE bridge');
        });
    }

    requestTasks() {
        this.socket?.send(JSON.stringify({ type: 'request_tasks' }));
    }

    private async handleMessage(raw: string) {
        try {
            const msg = JSON.parse(raw);
            switch (msg.type) {
                case 'tasks':
                    const tasks = (msg.tasks || []).join('\n');
                    if (tasks) {
                        vscode.window.showInformationMessage(`Tasks:\n${tasks}`);
                    }
                    break;
                case 'apply_patch':
                    await this.handlePatch(msg);
                    break;
            }
        } catch (err) {
            console.error('Failed to handle bridge message', err);
        }
    }

    private async handlePatch(msg: any) {
        const file = msg.file as string;
        const content = msg.content as string || '';
        const selection = await vscode.window.showInformationMessage(
            `Apply AI patch to ${file}?`,
            'Apply',
            'Reject'
        );

        const responseType = selection === 'Apply' ? 'patch_applied' : 'patch_rejected';
        if (selection === 'Apply') {
            const uri = vscode.Uri.file(file);
            await vscode.workspace.fs.writeFile(uri, Buffer.from(content, 'utf8'));
        }

        this.socket?.send(JSON.stringify({ type: responseType, file }));
    }
}
