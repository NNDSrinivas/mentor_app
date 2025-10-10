/**
 * AI Service - Advanced AI capabilities with offline support
 * Handles AI Brain communication, local processing, and context management
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import DeviceInfo from 'react-native-device-info';
import Voice from '@react-native-voice/voice';

interface AIRequest {
  context: any;
  type: 'meeting' | 'task' | 'code' | 'general';
  priority: 'low' | 'medium' | 'high';
  timestamp: number;
  userId?: string;
}

interface AIResponse {
  response: string;
  confidence: number;
  suggestions: string[];
  actions: Array<{
    type: string;
    payload: any;
    priority: number;
  }>;
  metadata: {
    processingTime: number;
    model: string;
    offline: boolean;
  };
}

export class AIService {
  private baseUrl: string = 'http://localhost:8000';
  private isInitialized: boolean = false;
  private isConnected: boolean = false;
  private contextProcessor: any;
  private offlineQueue: AIRequest[] = [];
  private localModels: Map<string, any> = new Map();
  private voiceEnabled: boolean = false;

  async initialize(): Promise<void> {
    try {
      // Check connectivity
      const netInfo = await NetInfo.fetch();
      this.isConnected = netInfo.isConnected || false;

      // Initialize local models for offline processing
      await this.initializeLocalModels();

      // Initialize voice recognition
      await this.initializeVoice();

      // Load offline queue
      await this.loadOfflineQueue();

      // Start context processor
      this.startContextProcessing();

      this.isInitialized = true;
      console.log('AI Service initialized');
    } catch (error) {
      console.error('AI Service initialization error:', error);
      throw error;
    }
  }

  private async initializeLocalModels(): Promise<void> {
    try {
      // Load pre-trained lightweight models for offline processing
      const modelData = await AsyncStorage.getItem('ai_models');
      if (modelData) {
        const models = JSON.parse(modelData);
        
        // Initialize text classification model
        this.localModels.set('textClassifier', {
          classify: this.classifyTextOffline.bind(this),
          confidence: 0.7
        });

        // Initialize sentiment analysis
        this.localModels.set('sentimentAnalyzer', {
          analyze: this.analyzeSentimentOffline.bind(this),
          confidence: 0.6
        });

        // Initialize basic NLP processor
        this.localModels.set('nlpProcessor', {
          process: this.processNLPOffline.bind(this),
          confidence: 0.5
        });
      }
    } catch (error) {
      console.warn('Local models initialization warning:', error);
    }
  }

  private async initializeVoice(): Promise<void> {
    try {
      // Check if voice recognition is available
      const available = await Voice.isAvailable();
      if (available) {
        Voice.onSpeechStart = this.onSpeechStart.bind(this);
        Voice.onSpeechEnd = this.onSpeechEnd.bind(this);
        Voice.onSpeechResults = this.onSpeechResults.bind(this);
        Voice.onSpeechError = this.onSpeechError.bind(this);
        
        this.voiceEnabled = true;
      }
    } catch (error) {
      console.warn('Voice initialization error:', error);
      this.voiceEnabled = false;
    }
  }

  async processRequest(request: AIRequest): Promise<AIResponse> {
    const startTime = Date.now();
    
    try {
      if (this.isConnected) {
        // Online processing - use AI Brain backend
        return await this.processOnline(request, startTime);
      } else {
        // Offline processing - use local models
        return await this.processOffline(request, startTime);
      }
    } catch (error) {
      console.error('AI request processing error:', error);
      
      // Fallback to offline processing
      if (this.isConnected) {
        return await this.processOffline(request, startTime);
      }
      
      throw error;
    }
  }

  private async processOnline(request: AIRequest, startTime: number): Promise<AIResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/ai-brain/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': `AI-SDLC-Mobile/${await DeviceInfo.getVersion()}`,
        },
        body: JSON.stringify({
          ...request,
          device: {
            platform: await DeviceInfo.getSystemName(),
            version: await DeviceInfo.getSystemVersion(),
            model: await DeviceInfo.getModel(),
          },
        }),
        timeout: 30000,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      return {
        response: data.response || 'No response generated',
        confidence: data.confidence || 0.8,
        suggestions: data.suggestions || [],
        actions: data.actions || [],
        metadata: {
          processingTime: Date.now() - startTime,
          model: data.model || 'ai-brain',
          offline: false,
        },
      };
    } catch (error) {
      console.error('Online processing error:', error);
      throw error;
    }
  }

  private async processOffline(request: AIRequest, startTime: number): Promise<AIResponse> {
    try {
      // Queue request for later sync if online processing was intended
      if (this.isConnected) {
        this.addToOfflineQueue(request);
      }

      // Process with local models
      const { context, type } = request;
      let response = '';
      let confidence = 0.5;
      let suggestions: string[] = [];
      let actions: any[] = [];

      switch (type) {
        case 'meeting':
          ({ response, confidence, suggestions, actions } = await this.processMeetingOffline(context));
          break;
        case 'task':
          ({ response, confidence, suggestions, actions } = await this.processTaskOffline(context));
          break;
        case 'code':
          ({ response, confidence, suggestions, actions } = await this.processCodeOffline(context));
          break;
        default:
          ({ response, confidence, suggestions, actions } = await this.processGeneralOffline(context));
      }

      return {
        response,
        confidence,
        suggestions,
        actions,
        metadata: {
          processingTime: Date.now() - startTime,
          model: 'local-offline',
          offline: true,
        },
      };
    } catch (error) {
      console.error('Offline processing error:', error);
      throw error;
    }
  }

  private async processMeetingOffline(context: any) {
    // Offline meeting analysis
    const text = context.text || '';
    const sentiment = this.analyzeSentimentOffline(text);
    const classification = this.classifyTextOffline(text);
    
    let response = 'Meeting analysis (offline): ';
    let suggestions = [];
    let actions = [];
    
    if (sentiment.score < -0.3) {
      response += 'Concerns detected in discussion. ';
      suggestions.push('Address concerns raised');
      actions.push({
        type: 'create_followup_task',
        payload: { priority: 'high', type: 'concern_resolution' },
        priority: 1,
      });
    } else if (sentiment.score > 0.3) {
      response += 'Positive discussion tone detected. ';
      suggestions.push('Capitalize on positive momentum');
    }
    
    if (classification.includes('decision') || classification.includes('action')) {
      suggestions.push('Document decisions and action items');
      actions.push({
        type: 'create_meeting_summary',
        payload: { includeDecisions: true, includeActions: true },
        priority: 2,
      });
    }
    
    return {
      response: response.trim(),
      confidence: 0.6,
      suggestions,
      actions,
    };
  }

  private async processTaskOffline(context: any) {
    // Offline task analysis
    const description = context.description || '';
    const classification = this.classifyTextOffline(description);
    
    let response = 'Task analysis (offline): ';
    let suggestions = [];
    let actions = [];
    
    // Estimate complexity
    const complexity = this.estimateComplexityOffline(description);
    response += `Estimated complexity: ${complexity}. `;
    
    if (complexity === 'high') {
      suggestions.push('Break down into smaller subtasks');
      actions.push({
        type: 'suggest_breakdown',
        payload: { taskId: context.id, complexity },
        priority: 1,
      });
    }
    
    // Suggest timeline
    const estimatedHours = this.estimateTimeOffline(description, complexity);
    suggestions.push(`Estimated time: ${estimatedHours} hours`);
    
    return {
      response: response.trim(),
      confidence: 0.5,
      suggestions,
      actions,
    };
  }

  private async processCodeOffline(context: any) {
    // Offline code analysis
    const code = context.code || '';
    const language = context.language || 'unknown';
    
    let response = 'Code analysis (offline): ';
    let suggestions = [];
    let actions = [];
    
    // Basic code quality checks
    const qualityScore = this.analyzeCodeQualityOffline(code, language);
    response += `Quality score: ${qualityScore}/10. `;
    
    if (qualityScore < 6) {
      suggestions.push('Consider refactoring for better quality');
      actions.push({
        type: 'suggest_refactoring',
        payload: { language, qualityScore },
        priority: 2,
      });
    }
    
    // Check for common patterns
    const patterns = this.detectPatternsOffline(code, language);
    if (patterns.length > 0) {
      suggestions.push(`Detected patterns: ${patterns.join(', ')}`);
    }
    
    return {
      response: response.trim(),
      confidence: 0.4,
      suggestions,
      actions,
    };
  }

  private async processGeneralOffline(context: any) {
    // General offline processing
    const text = context.text || JSON.stringify(context);
    const sentiment = this.analyzeSentimentOffline(text);
    const classification = this.classifyTextOffline(text);
    
    let response = 'Analysis (offline): ';
    let suggestions = [];
    let actions = [];
    
    if (sentiment.score !== 0) {
      response += `Sentiment: ${sentiment.label}. `;
    }
    
    if (classification.length > 0) {
      response += `Categories: ${classification.join(', ')}.`;
      suggestions.push('Review categorization when online');
    }
    
    return {
      response: response.trim(),
      confidence: 0.3,
      suggestions,
      actions,
    };
  }

  // Local AI processing methods
  private classifyTextOffline(text: string): string[] {
    const categories = [];
    const lowerText = text.toLowerCase();
    
    if (lowerText.includes('meeting') || lowerText.includes('discuss')) categories.push('meeting');
    if (lowerText.includes('task') || lowerText.includes('todo')) categories.push('task');
    if (lowerText.includes('code') || lowerText.includes('bug')) categories.push('code');
    if (lowerText.includes('decision') || lowerText.includes('decide')) categories.push('decision');
    if (lowerText.includes('action') || lowerText.includes('next step')) categories.push('action');
    
    return categories;
  }

  private analyzeSentimentOffline(text: string): { score: number; label: string } {
    // Simple rule-based sentiment analysis
    const positiveWords = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'perfect', 'love', 'best'];
    const negativeWords = ['bad', 'terrible', 'awful', 'hate', 'worst', 'problem', 'issue', 'concern'];
    
    const words = text.toLowerCase().split(/\s+/);
    let score = 0;
    
    words.forEach(word => {
      if (positiveWords.includes(word)) score += 1;
      if (negativeWords.includes(word)) score -= 1;
    });
    
    // Normalize score
    const normalizedScore = Math.max(-1, Math.min(1, score / words.length * 10));
    
    let label = 'neutral';
    if (normalizedScore > 0.3) label = 'positive';
    else if (normalizedScore < -0.3) label = 'negative';
    
    return { score: normalizedScore, label };
  }

  private processNLPOffline(text: string): any {
    // Basic NLP processing
    return {
      wordCount: text.split(/\s+/).length,
      sentences: text.split(/[.!?]+/).length,
      avgWordsPerSentence: text.split(/\s+/).length / text.split(/[.!?]+/).length,
    };
  }

  private estimateComplexityOffline(description: string): 'low' | 'medium' | 'high' {
    const complexityIndicators = {
      high: ['integrate', 'complex', 'algorithm', 'architecture', 'system', 'database', 'api'],
      medium: ['implement', 'create', 'build', 'develop', 'design'],
      low: ['fix', 'update', 'change', 'modify', 'adjust'],
    };
    
    const lowerDescription = description.toLowerCase();
    
    for (const [level, indicators] of Object.entries(complexityIndicators)) {
      if (indicators.some(indicator => lowerDescription.includes(indicator))) {
        return level as 'low' | 'medium' | 'high';
      }
    }
    
    return 'medium';
  }

  private estimateTimeOffline(description: string, complexity: string): number {
    const baseHours = {
      low: 2,
      medium: 8,
      high: 24,
    };
    
    let hours = baseHours[complexity as keyof typeof baseHours];
    
    // Adjust based on keywords
    const timeModifiers = {
      'quick': 0.5,
      'simple': 0.7,
      'complex': 1.5,
      'comprehensive': 2.0,
    };
    
    const lowerDescription = description.toLowerCase();
    for (const [keyword, modifier] of Object.entries(timeModifiers)) {
      if (lowerDescription.includes(keyword)) {
        hours *= modifier;
        break;
      }
    }
    
    return Math.round(hours);
  }

  private analyzeCodeQualityOffline(code: string, language: string): number {
    let score = 5; // Base score
    
    // Check for comments
    if (code.includes('//') || code.includes('/*') || code.includes('#')) {
      score += 1;
    }
    
    // Check for proper indentation (rough check)
    const lines = code.split('\n');
    const indentedLines = lines.filter(line => line.startsWith(' ') || line.startsWith('\t'));
    if (indentedLines.length > lines.length * 0.3) {
      score += 1;
    }
    
    // Check for long lines (potential readability issue)
    const longLines = lines.filter(line => line.length > 120);
    if (longLines.length > lines.length * 0.1) {
      score -= 1;
    }
    
    // Language-specific checks
    if (language === 'javascript' || language === 'typescript') {
      if (code.includes('console.log')) score -= 0.5; // Debug statements left in
      if (code.includes('var ')) score -= 0.5; // Old variable declaration
    }
    
    return Math.max(1, Math.min(10, score));
  }

  private detectPatternsOffline(code: string, language: string): string[] {
    const patterns = [];
    
    // Common patterns
    if (code.includes('async') && code.includes('await')) patterns.push('async/await');
    if (code.includes('try') && code.includes('catch')) patterns.push('error-handling');
    if (code.includes('class ')) patterns.push('object-oriented');
    if (code.includes('function') || code.includes('=>')) patterns.push('functional');
    
    return patterns;
  }

  // Voice recognition methods
  private onSpeechStart = (event: any) => {
    console.log('Speech recognition started');
  };

  private onSpeechEnd = (event: any) => {
    console.log('Speech recognition ended');
  };

  private onSpeechResults = (event: any) => {
    const results = event.value;
    if (results && results.length > 0) {
      const speechText = results[0];
      this.processSpeechInput(speechText);
    }
  };

  private onSpeechError = (event: any) => {
    console.error('Speech recognition error:', event.error);
  };

  async startVoiceRecognition(): Promise<void> {
    if (!this.voiceEnabled) {
      throw new Error('Voice recognition not available');
    }
    
    try {
      await Voice.start('en-US');
    } catch (error) {
      console.error('Voice start error:', error);
      throw error;
    }
  }

  async stopVoiceRecognition(): Promise<void> {
    try {
      await Voice.stop();
    } catch (error) {
      console.error('Voice stop error:', error);
    }
  }

  private async processSpeechInput(speechText: string): Promise<void> {
    try {
      // Process voice input as AI request
      const request: AIRequest = {
        context: { text: speechText, source: 'voice' },
        type: 'general',
        priority: 'medium',
        timestamp: Date.now(),
      };
      
      const response = await this.processRequest(request);
      
      // Handle voice response (could trigger TTS or UI update)
      this.handleVoiceResponse(response);
    } catch (error) {
      console.error('Speech processing error:', error);
    }
  }

  private handleVoiceResponse(response: AIResponse): void {
    // Could implement Text-to-Speech here
    console.log('Voice response:', response.response);
  }

  // Offline queue management
  private async loadOfflineQueue(): Promise<void> {
    try {
      const queueData = await AsyncStorage.getItem('ai_offline_queue');
      if (queueData) {
        this.offlineQueue = JSON.parse(queueData);
      }
    } catch (error) {
      console.warn('Failed to load offline queue:', error);
    }
  }

  private async saveOfflineQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem('ai_offline_queue', JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.warn('Failed to save offline queue:', error);
    }
  }

  private addToOfflineQueue(request: AIRequest): void {
    this.offlineQueue.push(request);
    this.saveOfflineQueue();
  }

  async processOfflineQueue(): Promise<void> {
    if (!this.isConnected || this.offlineQueue.length === 0) {
      return;
    }
    
    try {
      const processedRequests = [];
      
      for (const request of this.offlineQueue) {
        try {
          await this.processOnline(request, Date.now());
          processedRequests.push(request);
        } catch (error) {
          console.error('Failed to process queued request:', error);
          // Keep request in queue for retry
        }
      }
      
      // Remove processed requests
      this.offlineQueue = this.offlineQueue.filter(
        request => !processedRequests.includes(request)
      );
      
      await this.saveOfflineQueue();
    } catch (error) {
      console.error('Offline queue processing error:', error);
    }
  }

  // Context processing
  startContextProcessing(): void {
    // Start background context processing
    console.log('AI context processing started');
  }

  stop(): void {
    // Stop all AI services
    if (this.voiceEnabled) {
      Voice.destroy();
    }
    console.log('AI Service stopped');
  }

  // Utility methods
  isAvailable(): boolean {
    return this.isInitialized;
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  updateConnectionStatus(connected: boolean): void {
    this.isConnected = connected;
    
    if (connected) {
      // Process offline queue when connection is restored
      this.processOfflineQueue();
    }
  }

  async updateModels(): Promise<void> {
    if (!this.isConnected) return;
    
    try {
      // Download updated models when connected
      const response = await fetch(`${this.baseUrl}/api/models/latest`);
      if (response.ok) {
        const models = await response.json();
        await AsyncStorage.setItem('ai_models', JSON.stringify(models));
        await this.initializeLocalModels();
      }
    } catch (error) {
      console.warn('Model update failed:', error);
    }
  }
}
