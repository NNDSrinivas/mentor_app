/**
 * Redux Store Configuration
 */

import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { combineReducers } from '@reduxjs/toolkit';

// Reducers
import appReducer from './slices/appSlice';
import dashboardReducer from './slices/dashboardSlice';
import tasksReducer from './slices/tasksSlice';
import meetingsReducer from './slices/meetingsSlice';
import codeReducer from './slices/codeSlice';
import analyticsReducer from './slices/analyticsSlice';
import settingsReducer from './slices/settingsSlice';
import aiReducer from './slices/aiSlice';
import syncReducer from './slices/syncSlice';

const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  whitelist: ['settings', 'tasks', 'analytics'], // Only persist certain slices
  blacklist: ['sync'], // Don't persist real-time data
};

const rootReducer = combineReducers({
  app: appReducer,
  dashboard: dashboardReducer,
  tasks: tasksReducer,
  meetings: meetingsReducer,
  code: codeReducer,
  analytics: analyticsReducer,
  settings: settingsReducer,
  ai: aiReducer,
  sync: syncReducer,
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
  devTools: __DEV__,
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
