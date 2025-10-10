/**
 * Notification Service - Advanced notification management with intelligent scheduling
 * Handles push notifications, local notifications, and smart notification strategies
 */

import PushNotification from 'react-native-push-notification';
import AsyncStorage from '@react-native-async-storage/async-storage';
import BackgroundTimer from 'react-native-background-timer';
import { Platform } from 'react-native';

interface NotificationData {
  id: string;
  type: 'meeting' | 'task' | 'code' | 'reminder' | 'insight' | 'alert';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  scheduledTime?: Date;
  data?: any;
  actions?: Array<{
    id: string;
    title: string;
    action: string;
  }>;
  category?: string;
  sound?: string;
  badge?: number;
  repeats?: boolean;
  repeatType?: 'daily' | 'weekly' | 'monthly';
  groupId?: string;
}

interface NotificationSettings {
  enabled: boolean;
  meetingReminders: boolean;
  taskDeadlines: boolean;
  codeReviews: boolean;
  insights: boolean;
  quietHours: {
    enabled: boolean;
    start: string; // HH:MM format
    end: string;   // HH:MM format
  };
  priority: {
    low: boolean;
    medium: boolean;
    high: boolean;
    urgent: boolean;
  };
  sound: boolean;
  vibration: boolean;
  badge: boolean;
}

interface NotificationSchedule {
  id: string;
  notificationId: string;
  scheduledTime: Date;
  status: 'pending' | 'sent' | 'cancelled';
  retryCount: number;
  lastAttempt?: Date;
}

export class NotificationService {
  private isInitialized: boolean = false;
  private settings: NotificationSettings;
  private scheduledNotifications: Map<string, NotificationSchedule> = new Map();
  private notificationHistory: NotificationData[] = [];
  private processingInterval: any;

  constructor() {
    this.settings = this.getDefaultSettings();
  }

  async initialize(): Promise<void> {
    try {
      // Configure push notifications
      await this.configurePushNotifications();

      // Load settings
      await this.loadSettings();

      // Load scheduled notifications
      await this.loadScheduledNotifications();

      // Load notification history
      await this.loadNotificationHistory();

      // Start notification processing
      this.startNotificationProcessing();

      this.isInitialized = true;
      console.log('Notification Service initialized');
    } catch (error) {
      console.error('Notification Service initialization error:', error);
      throw error;
    }
  }

  private async configurePushNotifications(): Promise<void> {
    return new Promise((resolve, reject) => {
      PushNotification.configure({
        // Called when notification is received (both in foreground and background)
        onNotification: this.handleNotification.bind(this),

        // Called when notification action is pressed
        onAction: this.handleNotificationAction.bind(this),

        // Called when registration succeeds
        onRegister: (token) => {
          console.log('Push notification token:', token);
          this.savePushToken(token.token);
          resolve();
        },

        // Called when registration fails
        onRegistrationError: (err) => {
          console.error('Push notification registration error:', err);
          reject(err);
        },

        // IOS specific settings
        requestPermissions: Platform.OS === 'ios',
        
        // Android specific settings
        popInitialNotification: true,
        requestPermissions: true,

        // Common settings
        permissions: {
          alert: true,
          badge: true,
          sound: true,
        },
        
        // Android specific
        largeIcon: 'ic_launcher',
        smallIcon: 'ic_notification',
        vibrate: true,
        playSound: true,
        soundName: 'default',
      });

      // Create notification channels for Android
      if (Platform.OS === 'android') {
        this.createNotificationChannels();
      }
    });
  }

  private createNotificationChannels(): void {
    const channels = [
      {
        channelId: 'meeting_reminders',
        channelName: 'Meeting Reminders',
        channelDescription: 'Notifications for upcoming meetings',
        importance: 4, // HIGH
        vibrate: true,
        playSound: true,
      },
      {
        channelId: 'task_notifications',
        channelName: 'Task Notifications',
        channelDescription: 'Task deadlines and updates',
        importance: 3, // DEFAULT
        vibrate: true,
        playSound: true,
      },
      {
        channelId: 'code_reviews',
        channelName: 'Code Reviews',
        channelDescription: 'Code review requests and updates',
        importance: 3, // DEFAULT
        vibrate: true,
        playSound: true,
      },
      {
        channelId: 'insights',
        channelName: 'AI Insights',
        channelDescription: 'AI-generated insights and suggestions',
        importance: 2, // LOW
        vibrate: false,
        playSound: false,
      },
      {
        channelId: 'alerts',
        channelName: 'System Alerts',
        channelDescription: 'Important system notifications',
        importance: 4, // HIGH
        vibrate: true,
        playSound: true,
      },
    ];

    channels.forEach(channel => {
      PushNotification.createChannel(channel, (created) => {
        console.log(`Channel ${channel.channelId} created:`, created);
      });
    });
  }

  private handleNotification = (notification: any) => {
    console.log('Notification received:', notification);
    
    // Track notification in history
    this.addToHistory({
      id: notification.id || Date.now().toString(),
      type: notification.data?.type || 'alert',
      title: notification.title || 'Notification',
      message: notification.message || notification.body || '',
      priority: notification.data?.priority || 'medium',
      data: notification.data,
    });

    // Handle notification based on type
    if (notification.data?.type) {
      this.handleTypedNotification(notification);
    }

    // Auto-cancel if needed
    if (notification.data?.autoCancel !== false) {
      setTimeout(() => {
        PushNotification.cancelLocalNotifications({ id: notification.id });
      }, 30000); // Auto-cancel after 30 seconds
    }
  };

  private handleNotificationAction = (notification: any) => {
    console.log('Notification action:', notification);
    
    const { action, userInfo } = notification;
    
    switch (action) {
      case 'View Details':
        this.handleViewDetails(userInfo);
        break;
      case 'Join Meeting':
        this.handleJoinMeeting(userInfo);
        break;
      case 'Mark Complete':
        this.handleMarkComplete(userInfo);
        break;
      case 'Snooze':
        this.handleSnooze(userInfo);
        break;
      default:
        console.log('Unknown notification action:', action);
    }
  };

  private handleTypedNotification(notification: any): void {
    const { type, data } = notification.data || {};
    
    switch (type) {
      case 'meeting':
        this.handleMeetingNotification(data);
        break;
      case 'task':
        this.handleTaskNotification(data);
        break;
      case 'code':
        this.handleCodeNotification(data);
        break;
      case 'insight':
        this.handleInsightNotification(data);
        break;
      default:
        console.log('Unknown notification type:', type);
    }
  }

  private handleMeetingNotification(data: any): void {
    // Handle meeting-specific notification logic
    console.log('Handling meeting notification:', data);
  }

  private handleTaskNotification(data: any): void {
    // Handle task-specific notification logic
    console.log('Handling task notification:', data);
  }

  private handleCodeNotification(data: any): void {
    // Handle code-specific notification logic
    console.log('Handling code notification:', data);
  }

  private handleInsightNotification(data: any): void {
    // Handle insight-specific notification logic
    console.log('Handling insight notification:', data);
  }

  private handleViewDetails(userInfo: any): void {
    // Navigate to relevant screen or show details
    console.log('View details for:', userInfo);
  }

  private handleJoinMeeting(userInfo: any): void {
    // Open meeting URL or join meeting
    console.log('Join meeting:', userInfo);
  }

  private handleMarkComplete(userInfo: any): void {
    // Mark task or item as complete
    console.log('Mark complete:', userInfo);
  }

  private handleSnooze(userInfo: any): void {
    // Snooze notification for later
    const snoozeTime = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes
    this.scheduleNotification({
      ...userInfo.originalNotification,
      id: `${userInfo.originalNotification.id}_snoozed`,
      scheduledTime: snoozeTime,
    });
  }

  async scheduleNotification(notification: NotificationData): Promise<void> {
    if (!this.shouldSendNotification(notification)) {
      console.log('Notification blocked by settings:', notification.type);
      return;
    }

    try {
      const scheduleId = `schedule_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      if (notification.scheduledTime) {
        // Schedule for future delivery
        const schedule: NotificationSchedule = {
          id: scheduleId,
          notificationId: notification.id,
          scheduledTime: notification.scheduledTime,
          status: 'pending',
          retryCount: 0,
        };
        
        this.scheduledNotifications.set(scheduleId, schedule);
        await this.saveScheduledNotifications();
        
        // Schedule with system
        PushNotification.localNotificationSchedule({
          id: notification.id,
          title: notification.title,
          message: notification.message,
          date: notification.scheduledTime,
          soundName: notification.sound || (this.settings.sound ? 'default' : null),
          playSound: this.settings.sound,
          vibrate: this.settings.vibration,
          number: notification.badge,
          repeatType: notification.repeatType,
          actions: notification.actions?.map(action => action.title) || [],
          category: notification.category || this.getChannelForType(notification.type),
          userInfo: {
            type: notification.type,
            priority: notification.priority,
            data: notification.data,
            originalNotification: notification,
          },
        });
      } else {
        // Send immediately
        this.sendLocalNotification(notification);
      }
      
      console.log(`Notification scheduled: ${notification.title}`);
    } catch (error) {
      console.error('Failed to schedule notification:', error);
    }
  }

  sendLocalNotification(notification: NotificationData): void {
    if (!this.shouldSendNotification(notification)) {
      console.log('Notification blocked by settings:', notification.type);
      return;
    }

    try {
      PushNotification.localNotification({
        id: notification.id,
        title: notification.title,
        message: notification.message,
        soundName: notification.sound || (this.settings.sound ? 'default' : null),
        playSound: this.settings.sound,
        vibrate: this.settings.vibration,
        number: notification.badge,
        actions: notification.actions?.map(action => action.title) || [],
        category: notification.category || this.getChannelForType(notification.type),
        userInfo: {
          type: notification.type,
          priority: notification.priority,
          data: notification.data,
          originalNotification: notification,
        },
      });
      
      this.addToHistory(notification);
      console.log(`Local notification sent: ${notification.title}`);
    } catch (error) {
      console.error('Failed to send local notification:', error);
    }
  }

  showLocalNotification(title: string, message: string, type: string = 'alert'): void {
    const notification: NotificationData = {
      id: Date.now().toString(),
      type: type as any,
      title,
      message,
      priority: 'medium',
    };
    
    this.sendLocalNotification(notification);
  }

  private shouldSendNotification(notification: NotificationData): boolean {
    // Check if notifications are enabled
    if (!this.settings.enabled) return false;
    
    // Check type-specific settings
    switch (notification.type) {
      case 'meeting':
        if (!this.settings.meetingReminders) return false;
        break;
      case 'task':
        if (!this.settings.taskDeadlines) return false;
        break;
      case 'code':
        if (!this.settings.codeReviews) return false;
        break;
      case 'insight':
        if (!this.settings.insights) return false;
        break;
    }
    
    // Check priority settings
    if (!this.settings.priority[notification.priority]) return false;
    
    // Check quiet hours
    if (this.isQuietHours()) {
      // Only allow urgent notifications during quiet hours
      return notification.priority === 'urgent';
    }
    
    return true;
  }

  private isQuietHours(): boolean {
    if (!this.settings.quietHours.enabled) return false;
    
    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    const start = this.settings.quietHours.start;
    const end = this.settings.quietHours.end;
    
    // Handle overnight quiet hours (e.g., 22:00 to 08:00)
    if (start > end) {
      return currentTime >= start || currentTime <= end;
    } else {
      return currentTime >= start && currentTime <= end;
    }
  }

  private getChannelForType(type: string): string {
    const channels = {
      meeting: 'meeting_reminders',
      task: 'task_notifications',
      code: 'code_reviews',
      insight: 'insights',
      alert: 'alerts',
      reminder: 'alerts',
    };
    
    return channels[type as keyof typeof channels] || 'alerts';
  }

  async cancelNotification(notificationId: string): Promise<void> {
    try {
      PushNotification.cancelLocalNotifications({ id: notificationId });
      
      // Remove from scheduled notifications
      for (const [scheduleId, schedule] of this.scheduledNotifications.entries()) {
        if (schedule.notificationId === notificationId) {
          schedule.status = 'cancelled';
          this.scheduledNotifications.set(scheduleId, schedule);
          break;
        }
      }
      
      await this.saveScheduledNotifications();
      console.log(`Notification cancelled: ${notificationId}`);
    } catch (error) {
      console.error('Failed to cancel notification:', error);
    }
  }

  async cancelAllNotifications(): Promise<void> {
    try {
      PushNotification.cancelAllLocalNotifications();
      
      // Mark all scheduled as cancelled
      for (const [scheduleId, schedule] of this.scheduledNotifications.entries()) {
        schedule.status = 'cancelled';
        this.scheduledNotifications.set(scheduleId, schedule);
      }
      
      await this.saveScheduledNotifications();
      console.log('All notifications cancelled');
    } catch (error) {
      console.error('Failed to cancel all notifications:', error);
    }
  }

  async updateBadgeCount(count?: number): Promise<void> {
    try {
      if (count === undefined) {
        // Auto-calculate badge count
        count = this.calculateBadgeCount();
      }
      
      PushNotification.setApplicationIconBadgeNumber(count);
      console.log(`Badge count updated: ${count}`);
    } catch (error) {
      console.error('Failed to update badge count:', error);
    }
  }

  private calculateBadgeCount(): number {
    // Calculate based on pending items
    let count = 0;
    
    // Add unread notifications from last 24 hours
    const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentNotifications = this.notificationHistory.filter(
      n => new Date(n.scheduledTime || 0) > dayAgo
    );
    count += recentNotifications.length;
    
    return Math.min(99, count); // Cap at 99
  }

  private startNotificationProcessing(): void {
    this.processingInterval = BackgroundTimer.setInterval(async () => {
      try {
        await this.processScheduledNotifications();
        await this.cleanupOldNotifications();
      } catch (error) {
        console.error('Notification processing error:', error);
      }
    }, 60000); // Process every minute
    
    console.log('Notification processing started');
  }

  private async processScheduledNotifications(): Promise<void> {
    const now = new Date();
    
    for (const [scheduleId, schedule] of this.scheduledNotifications.entries()) {
      if (schedule.status === 'pending' && schedule.scheduledTime <= now) {
        try {
          // Find the original notification
          const notification = this.findNotificationById(schedule.notificationId);
          if (notification) {
            this.sendLocalNotification(notification);
            schedule.status = 'sent';
            schedule.lastAttempt = now;
          } else {
            schedule.status = 'cancelled';
          }
          
          this.scheduledNotifications.set(scheduleId, schedule);
        } catch (error) {
          console.error('Failed to process scheduled notification:', error);
          schedule.retryCount++;
          schedule.lastAttempt = now;
          
          if (schedule.retryCount >= 3) {
            schedule.status = 'cancelled';
          }
          
          this.scheduledNotifications.set(scheduleId, schedule);
        }
      }
    }
    
    await this.saveScheduledNotifications();
  }

  private async cleanupOldNotifications(): Promise<void> {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    
    // Clean up old scheduled notifications
    for (const [scheduleId, schedule] of this.scheduledNotifications.entries()) {
      if (schedule.scheduledTime < weekAgo && schedule.status !== 'pending') {
        this.scheduledNotifications.delete(scheduleId);
      }
    }
    
    // Clean up old notification history
    this.notificationHistory = this.notificationHistory.filter(
      notification => {
        const notificationTime = new Date(notification.scheduledTime || 0);
        return notificationTime > weekAgo;
      }
    );
    
    await this.saveScheduledNotifications();
    await this.saveNotificationHistory();
  }

  private findNotificationById(notificationId: string): NotificationData | null {
    return this.notificationHistory.find(n => n.id === notificationId) || null;
  }

  private addToHistory(notification: NotificationData): void {
    this.notificationHistory.unshift(notification);
    
    // Keep only last 100 notifications
    if (this.notificationHistory.length > 100) {
      this.notificationHistory = this.notificationHistory.slice(0, 100);
    }
    
    this.saveNotificationHistory();
  }

  // Settings management
  async updateSettings(newSettings: Partial<NotificationSettings>): Promise<void> {
    this.settings = { ...this.settings, ...newSettings };
    await this.saveSettings();
    console.log('Notification settings updated');
  }

  getSettings(): NotificationSettings {
    return { ...this.settings };
  }

  private getDefaultSettings(): NotificationSettings {
    return {
      enabled: true,
      meetingReminders: true,
      taskDeadlines: true,
      codeReviews: true,
      insights: true,
      quietHours: {
        enabled: false,
        start: '22:00',
        end: '08:00',
      },
      priority: {
        low: true,
        medium: true,
        high: true,
        urgent: true,
      },
      sound: true,
      vibration: true,
      badge: true,
    };
  }

  private async loadSettings(): Promise<void> {
    try {
      const settingsData = await AsyncStorage.getItem('notification_settings');
      if (settingsData) {
        this.settings = { ...this.settings, ...JSON.parse(settingsData) };
      }
    } catch (error) {
      console.error('Failed to load notification settings:', error);
    }
  }

  private async saveSettings(): Promise<void> {
    try {
      await AsyncStorage.setItem('notification_settings', JSON.stringify(this.settings));
    } catch (error) {
      console.error('Failed to save notification settings:', error);
    }
  }

  private async loadScheduledNotifications(): Promise<void> {
    try {
      const scheduledData = await AsyncStorage.getItem('scheduled_notifications');
      if (scheduledData) {
        const scheduled = JSON.parse(scheduledData);
        this.scheduledNotifications = new Map(Object.entries(scheduled));
      }
    } catch (error) {
      console.error('Failed to load scheduled notifications:', error);
    }
  }

  private async saveScheduledNotifications(): Promise<void> {
    try {
      const scheduledObj = Object.fromEntries(this.scheduledNotifications);
      await AsyncStorage.setItem('scheduled_notifications', JSON.stringify(scheduledObj));
    } catch (error) {
      console.error('Failed to save scheduled notifications:', error);
    }
  }

  private async loadNotificationHistory(): Promise<void> {
    try {
      const historyData = await AsyncStorage.getItem('notification_history');
      if (historyData) {
        this.notificationHistory = JSON.parse(historyData);
      }
    } catch (error) {
      console.error('Failed to load notification history:', error);
    }
  }

  private async saveNotificationHistory(): Promise<void> {
    try {
      await AsyncStorage.setItem('notification_history', JSON.stringify(this.notificationHistory));
    } catch (error) {
      console.error('Failed to save notification history:', error);
    }
  }

  private async savePushToken(token: string): Promise<void> {
    try {
      await AsyncStorage.setItem('push_token', token);
      console.log('Push token saved');
    } catch (error) {
      console.error('Failed to save push token:', error);
    }
  }

  async getPushToken(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem('push_token');
    } catch (error) {
      console.error('Failed to get push token:', error);
      return null;
    }
  }

  // Utility methods
  getNotificationHistory(): NotificationData[] {
    return [...this.notificationHistory];
  }

  getScheduledNotifications(): NotificationSchedule[] {
    return Array.from(this.scheduledNotifications.values());
  }

  getPendingNotificationsCount(): number {
    return Array.from(this.scheduledNotifications.values())
      .filter(schedule => schedule.status === 'pending').length;
  }

  async exportNotificationData(): Promise<string> {
    try {
      const exportData = {
        settings: this.settings,
        scheduled: Object.fromEntries(this.scheduledNotifications),
        history: this.notificationHistory,
        exportDate: new Date().toISOString(),
      };
      
      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      console.error('Notification export error:', error);
      throw error;
    }
  }

  stop(): void {
    if (this.processingInterval) {
      BackgroundTimer.clearInterval(this.processingInterval);
      this.processingInterval = null;
    }
    
    console.log('Notification Service stopped');
  }
}
