/**
 * Settings Slice - App configuration and preferences
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface NotificationSettings {
  enabled: boolean;
  sound: boolean;
  vibration: boolean;
  quietHours: {
    enabled: boolean;
    start: string; // HH:MM format
    end: string; // HH:MM format
  };
  meetingReminders: {
    enabled: boolean;
    timing: number[]; // minutes before meeting
  };
  taskDeadlines: boolean;
  aiInsights: boolean;
  syncUpdates: boolean;
}

export interface PrivacySettings {
  dataCollection: boolean;
  analytics: boolean;
  crashReporting: boolean;
  personalizedAI: boolean;
  shareUsageData: boolean;
}

export interface SyncSettings {
  autoSync: boolean;
  syncInterval: number; // minutes
  syncOnWiFiOnly: boolean;
  backgroundSync: boolean;
  conflictResolution: 'manual' | 'auto_local' | 'auto_remote';
}

export interface AISettings {
  offlineMode: boolean;
  modelPreference: 'speed' | 'quality' | 'balanced';
  contextWindow: number;
  personalizedResponses: boolean;
  voiceInput: boolean;
  autoSuggestions: boolean;
  confidenceThreshold: number;
}

export interface SettingsState {
  notifications: NotificationSettings;
  privacy: PrivacySettings;
  sync: SyncSettings;
  ai: AISettings;
  appearance: {
    theme: 'light' | 'dark' | 'auto';
    fontSize: 'small' | 'medium' | 'large';
    language: string;
    colorScheme: string;
  };
  accessibility: {
    highContrast: boolean;
    reducedMotion: boolean;
    screenReader: boolean;
    largeText: boolean;
  };
  developer: {
    debugMode: boolean;
    showPerformanceMetrics: boolean;
    enableBetaFeatures: boolean;
    logLevel: 'error' | 'warn' | 'info' | 'debug';
  };
  backup: {
    autoBackup: boolean;
    backupFrequency: 'daily' | 'weekly' | 'monthly';
    cloudBackup: boolean;
    encryptBackups: boolean;
  };
}

const initialState: SettingsState = {
  notifications: {
    enabled: true,
    sound: true,
    vibration: true,
    quietHours: {
      enabled: true,
      start: '22:00',
      end: '08:00',
    },
    meetingReminders: {
      enabled: true,
      timing: [15, 5], // 15 and 5 minutes before
    },
    taskDeadlines: true,
    aiInsights: true,
    syncUpdates: false,
  },
  privacy: {
    dataCollection: true,
    analytics: true,
    crashReporting: true,
    personalizedAI: true,
    shareUsageData: false,
  },
  sync: {
    autoSync: true,
    syncInterval: 5, // 5 minutes
    syncOnWiFiOnly: false,
    backgroundSync: true,
    conflictResolution: 'manual',
  },
  ai: {
    offlineMode: true,
    modelPreference: 'balanced',
    contextWindow: 4000,
    personalizedResponses: true,
    voiceInput: true,
    autoSuggestions: true,
    confidenceThreshold: 0.7,
  },
  appearance: {
    theme: 'auto',
    fontSize: 'medium',
    language: 'en',
    colorScheme: 'default',
  },
  accessibility: {
    highContrast: false,
    reducedMotion: false,
    screenReader: false,
    largeText: false,
  },
  developer: {
    debugMode: false,
    showPerformanceMetrics: false,
    enableBetaFeatures: false,
    logLevel: 'error',
  },
  backup: {
    autoBackup: true,
    backupFrequency: 'weekly',
    cloudBackup: false,
    encryptBackups: true,
  },
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState,
  reducers: {
    updateNotificationSettings: (state, action: PayloadAction<Partial<NotificationSettings>>) => {
      state.notifications = { ...state.notifications, ...action.payload };
    },
    updatePrivacySettings: (state, action: PayloadAction<Partial<PrivacySettings>>) => {
      state.privacy = { ...state.privacy, ...action.payload };
    },
    updateSyncSettings: (state, action: PayloadAction<Partial<SyncSettings>>) => {
      state.sync = { ...state.sync, ...action.payload };
    },
    updateAISettings: (state, action: PayloadAction<Partial<AISettings>>) => {
      state.ai = { ...state.ai, ...action.payload };
    },
    updateAppearanceSettings: (state, action: PayloadAction<Partial<SettingsState['appearance']>>) => {
      state.appearance = { ...state.appearance, ...action.payload };
    },
    updateAccessibilitySettings: (state, action: PayloadAction<Partial<SettingsState['accessibility']>>) => {
      state.accessibility = { ...state.accessibility, ...action.payload };
    },
    updateDeveloperSettings: (state, action: PayloadAction<Partial<SettingsState['developer']>>) => {
      state.developer = { ...state.developer, ...action.payload };
    },
    updateBackupSettings: (state, action: PayloadAction<Partial<SettingsState['backup']>>) => {
      state.backup = { ...state.backup, ...action.payload };
    },
    resetToDefaults: (state) => {
      return initialState;
    },
    importSettings: (state, action: PayloadAction<Partial<SettingsState>>) => {
      return { ...state, ...action.payload };
    },
    toggleQuietHours: (state) => {
      state.notifications.quietHours.enabled = !state.notifications.quietHours.enabled;
    },
    setMeetingReminderTiming: (state, action: PayloadAction<number[]>) => {
      state.notifications.meetingReminders.timing = action.payload;
    },
    toggleOfflineMode: (state) => {
      state.ai.offlineMode = !state.ai.offlineMode;
    },
    setConflictResolution: (state, action: PayloadAction<SyncSettings['conflictResolution']>) => {
      state.sync.conflictResolution = action.payload;
    },
    updateQuietHours: (state, action: PayloadAction<{ start: string; end: string }>) => {
      state.notifications.quietHours.start = action.payload.start;
      state.notifications.quietHours.end = action.payload.end;
    },
  },
});

export const {
  updateNotificationSettings,
  updatePrivacySettings,
  updateSyncSettings,
  updateAISettings,
  updateAppearanceSettings,
  updateAccessibilitySettings,
  updateDeveloperSettings,
  updateBackupSettings,
  resetToDefaults,
  importSettings,
  toggleQuietHours,
  setMeetingReminderTiming,
  toggleOfflineMode,
  setConflictResolution,
  updateQuietHours,
} = settingsSlice.actions;

export default settingsSlice.reducer;
