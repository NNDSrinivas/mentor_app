/**
 * Redux Store Configuration
 */

import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { combineReducers } from '@reduxjs/toolkit';

// Reducers
import appReducer from './slices/appSlice';
import { dashboardSlice, codeSlice, analyticsSlice, aiSlice, syncSlice } from './slices';
import tasksReducer from './slices/tasksSlice';
import meetingsReducer from './slices/meetingsSlice';
import settingsReducer from './slices/settingsSlice';

const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  whitelist: ['settings', 'tasks', 'analytics'], // Only persist certain slices
  blacklist: ['sync'], // Don't persist real-time data
};

const rootReducer = combineReducers({
  app: appReducer,
  dashboard: dashboardSlice.reducer,
  tasks: tasksReducer,
  meetings: meetingsReducer,
  code: codeSlice.reducer,
  analytics: analyticsSlice.reducer,
  settings: settingsReducer,
  ai: aiSlice.reducer,
  sync: syncSlice.reducer,
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
