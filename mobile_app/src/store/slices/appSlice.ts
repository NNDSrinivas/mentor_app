/**
 * App Slice - Global app state
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AppState {
  isLoading: boolean;
  isConnected: boolean;
  currentScreen: string;
  notification: {
    visible: boolean;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
  } | null;
  theme: 'light' | 'dark' | 'auto';
  language: string;
  firstLaunch: boolean;
  lastSync: Date | null;
}

const initialState: AppState = {
  isLoading: false,
  isConnected: false,
  currentScreen: 'Dashboard',
  notification: null,
  theme: 'auto',
  language: 'en',
  firstLaunch: true,
  lastSync: null,
};

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },
    setCurrentScreen: (state, action: PayloadAction<string>) => {
      state.currentScreen = action.payload;
    },
    showNotification: (state, action: PayloadAction<{
      message: string;
      type: 'success' | 'error' | 'warning' | 'info';
    }>) => {
      state.notification = {
        visible: true,
        ...action.payload,
      };
    },
    hideNotification: (state) => {
      state.notification = null;
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'auto'>) => {
      state.theme = action.payload;
    },
    setLanguage: (state, action: PayloadAction<string>) => {
      state.language = action.payload;
    },
    setFirstLaunch: (state, action: PayloadAction<boolean>) => {
      state.firstLaunch = action.payload;
    },
    setLastSync: (state, action: PayloadAction<Date | null>) => {
      state.lastSync = action.payload;
    },
  },
});

export const {
  setLoading,
  setConnected,
  setCurrentScreen,
  showNotification,
  hideNotification,
  setTheme,
  setLanguage,
  setFirstLaunch,
  setLastSync,
} = appSlice.actions;

export default appSlice.reducer;
