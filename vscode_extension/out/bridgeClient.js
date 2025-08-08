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
exports.BridgeClient = void 0;
const ws_1 = __importDefault(require("ws"));
const vscode = __importStar(require("vscode"));
/**
 * Simple WebSocket client for communicating with the Python IDE bridge.
 */
class BridgeClient {
    constructor(url) {
        this.url = url;
        this.socket = null;
    }
    connect() {
        this.socket = new ws_1.default(this.url);
        this.socket.on('open', () => {
            console.log('🔌 Connected to IDE bridge');
        });
        this.socket.on('message', async (data) => {
            await this.handleMessage(data.toString());
        });
        this.socket.on('close', () => {
            console.log('❌ Disconnected from IDE bridge');
        });
    }
    requestTasks() {
        this.socket?.send(JSON.stringify({ type: 'request_tasks' }));
    }
    async handleMessage(raw) {
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
        }
        catch (err) {
            console.error('Failed to handle bridge message', err);
        }
    }
    async handlePatch(msg) {
        const file = msg.file;
        const content = msg.content || '';
        const selection = await vscode.window.showInformationMessage(`Apply AI patch to ${file}?`, 'Apply', 'Reject');
        const responseType = selection === 'Apply' ? 'patch_applied' : 'patch_rejected';
        if (selection === 'Apply') {
            const uri = vscode.Uri.file(file);
            await vscode.workspace.fs.writeFile(uri, Buffer.from(content, 'utf8'));
        }
        this.socket?.send(JSON.stringify({ type: responseType, file }));
    }
}
exports.BridgeClient = BridgeClient;
//# sourceMappingURL=bridgeClient.js.map