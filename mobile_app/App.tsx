/**
 * AI SDLC Assistant Mobile App - Main Application Component
 * Advanced mobile app with offline capabilities, notifications, and calendar integration
 */

import React, { useEffect, useCallback } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { StatusBar, Platform, Alert, AppState } from 'react-native';
import { Provider as PaperProvider } from 'react-native-paper';
import NetInfo from '@react-native-community/netinfo';
import PushNotification from 'react-native-push-notification';
import BackgroundTimer from 'react-native-background-timer';
import DeviceInfo from 'react-native-device-info';

// Redux Store
import { store, persistor } from './src/redux/store';

// Screens
import DashboardScreen from './src/screens/DashboardScreen';
import MeetingScreen from './src/screens/MeetingScreen';
import TasksScreen from './src/screens/TasksScreen';
import CodeScreen from './src/screens/CodeScreen';
import AnalyticsScreen from './src/screens/AnalyticsScreen';
import SettingsScreen from './src/screens/SettingsScreen';

// Services
import { AIService } from './src/services/AIService';
import { SyncService } from './src/services/SyncService';
import { NotificationService } from './src/services/NotificationService';
import { CalendarService } from './src/services/CalendarService';
import { OfflineService } from './src/services/OfflineService';

// Components
import LoadingScreen from './src/components/LoadingScreen';
import IconTabBar from './src/components/IconTabBar';

// Theme
import { theme } from './src/theme';

// Types
import { AppStateType } from './src/types';

const Tab = createBottomTabNavigator();

class App extends React.Component {
  state: AppStateType = {
    isLoading: true,
    isConnected: false,
    backgroundSyncEnabled: true,
    lastSyncTime: null,
    appState: AppState.currentState
  };

  private aiService: AIService;
  private syncService: SyncService;
  private notificationService: NotificationService;
  private calendarService: CalendarService;
  private offlineService: OfflineService;
  private backgroundSyncInterval: any;

  constructor(props: any) {
    super(props);
    
    // Initialize services
    this.aiService = new AIService();
    this.syncService = new SyncService();
    this.notificationService = new NotificationService();
    this.calendarService = new CalendarService();
    this.offlineService = new OfflineService();
  }

  async componentDidMount() {
    await this.initializeApp();
    this.setupEventListeners();
    this.startBackgroundServices();
  }

  componentWillUnmount() {
    this.cleanup();
  }

  private async initializeApp() {
    try {
      // Initialize core services
      await Promise.all([
        this.aiService.initialize(),
        this.syncService.initialize(),
        this.notificationService.initialize(),
        this.calendarService.initialize(),
        this.offlineService.initialize()
      ]);

      // Check connectivity
      const netInfo = await NetInfo.fetch();
      this.setState({ isConnected: netInfo.isConnected });

      // Initial sync if connected
      if (netInfo.isConnected) {
        await this.performInitialSync();
      }

      this.setState({ isLoading: false });
      
    } catch (error) {
      console.error('App initialization error:', error);
      Alert.alert('Initialization Error', 'Failed to initialize app. Some features may not work.');
      this.setState({ isLoading: false });
    }
  }

  private setupEventListeners() {
    // Network connectivity
    NetInfo.addEventListener(state => {
      const wasConnected = this.state.isConnected;
      const isConnected = state.isConnected;
      
      this.setState({ isConnected });

      if (!wasConnected && isConnected) {
        // Just came online
        this.handleOnlineReconnection();
      } else if (wasConnected && !isConnected) {
        // Just went offline
        this.handleOfflineTransition();
      }
    });

    // App state changes
    AppState.addEventListener('change', this.handleAppStateChange);

    // Push notifications
    PushNotification.configure({
      onNotification: this.handleNotification,
      onAction: this.handleNotificationAction,
      onRegistrationError: (err) => {
        console.error('Push notification registration error:', err);
      },
      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },
      requestPermissions: Platform.OS === 'ios',
    });
  }

  private handleAppStateChange = (nextAppState: string) => {
    const { appState } = this.state;
    
    if (appState.match(/inactive|background/) && nextAppState === 'active') {
      // App came to foreground
      this.handleAppForeground();
    } else if (appState === 'active' && nextAppState.match(/inactive|background/)) {
      // App went to background
      this.handleAppBackground();
    }
    
    this.setState({ appState: nextAppState });
  };

  private async handleAppForeground() {
    try {
      // Refresh data when app comes to foreground
      if (this.state.isConnected) {
        await this.syncService.performQuickSync();
      }
      
      // Update notifications
      await this.notificationService.updateBadgeCount();
      
      // Refresh calendar events
      await this.calendarService.refreshUpcomingEvents();
      
    } catch (error) {
      console.error('Foreground handling error:', error);
    }
  }

  private async handleAppBackground() {
    try {
      // Save current state
      await this.offlineService.saveCurrentState();
      
      // Schedule background sync if enabled
      if (this.state.backgroundSyncEnabled && this.state.isConnected) {
        this.scheduleBackgroundSync();
      }
      
    } catch (error) {
      console.error('Background handling error:', error);
    }
  }

  private async handleOnlineReconnection() {
    try {
      // Sync offline changes
      await this.syncService.syncOfflineChanges();
      
      // Update AI models if needed
      await this.aiService.updateModels();
      
      // Refresh all data
      await this.performFullSync();
      
      this.notificationService.showLocalNotification(
        'Back Online',
        'Syncing your latest changes...'
      );
      
    } catch (error) {
      console.error('Online reconnection error:', error);
    }
  }

  private async handleOfflineTransition() {
    try {
      // Enable offline mode
      await this.offlineService.enableOfflineMode();
      
      this.notificationService.showLocalNotification(
        'Offline Mode',
        'Working offline. Changes will sync when connected.'
      );
      
    } catch (error) {
      console.error('Offline transition error:', error);
    }
  }

  private handleNotification = (notification: any) => {
    console.log('Notification received:', notification);
    
    // Handle different notification types
    const { type, data } = notification;
    
    switch (type) {
      case 'meeting_reminder':
        this.handleMeetingReminder(data);
        break;
      case 'task_update':
        this.handleTaskUpdate(data);
        break;
      case 'code_review':
        this.handleCodeReview(data);
        break;
      default:
        // Default notification handling
        break;
    }
  };

  private handleNotificationAction = (action: any) => {
    console.log('Notification action:', action);
    // Handle notification actions (buttons, etc.)
  };

  private async handleMeetingReminder(data: any) {
    // Navigate to meeting screen or show meeting details
    try {
      await this.calendarService.prepareMeetingContext(data.meetingId);
    } catch (error) {
      console.error('Meeting reminder error:', error);
    }
  }

  private async handleTaskUpdate(data: any) {
    // Refresh task data and show update
    try {
      await this.syncService.syncTaskData(data.taskId);
    } catch (error) {
      console.error('Task update error:', error);
    }
  }

  private async handleCodeReview(data: any) {
    // Show code review notification
    try {
      await this.syncService.syncCodeData(data.reviewId);
    } catch (error) {
      console.error('Code review error:', error);
    }
  }

  private startBackgroundServices() {
    // Start background sync timer
    this.backgroundSyncInterval = BackgroundTimer.setInterval(async () => {
      if (this.state.isConnected && this.state.backgroundSyncEnabled) {
        try {
          await this.syncService.performBackgroundSync();
          this.setState({ lastSyncTime: new Date() });
        } catch (error) {
          console.error('Background sync error:', error);
        }
      }
    }, 300000); // 5 minutes

    // Start AI context processing
    this.aiService.startContextProcessing();
    
    // Start calendar monitoring
    this.calendarService.startEventMonitoring();
  }

  private async performInitialSync() {
    try {
      await Promise.all([
        this.syncService.syncUserProfile(),
        this.syncService.syncMeetings(),
        this.syncService.syncTasks(),
        this.syncService.syncCodeData(),
        this.calendarService.syncCalendarEvents()
      ]);
      
      this.setState({ lastSyncTime: new Date() });
    } catch (error) {
      console.error('Initial sync error:', error);
    }
  }

  private async performFullSync() {
    try {
      await this.syncService.performFullSync();
      this.setState({ lastSyncTime: new Date() });
    } catch (error) {
      console.error('Full sync error:', error);
    }
  }

  private scheduleBackgroundSync() {
    // Schedule background sync using BackgroundTimer
    BackgroundTimer.setTimeout(async () => {
      try {
        await this.syncService.performBackgroundSync();
      } catch (error) {
        console.error('Scheduled background sync error:', error);
      }
    }, 60000); // 1 minute delay
  }

  private cleanup() {
    // Clear intervals
    if (this.backgroundSyncInterval) {
      BackgroundTimer.clearInterval(this.backgroundSyncInterval);
    }
    
    // Stop services
    this.aiService.stop();
    this.calendarService.stopEventMonitoring();
    
    // Remove listeners
    AppState.removeEventListener('change', this.handleAppStateChange);
  }

  render() {
    if (this.state.isLoading) {
      return <LoadingScreen />;
    }

    return (
      <Provider store={store}>
        <PersistGate loading={<LoadingScreen />} persistor={persistor}>
          <PaperProvider theme={theme}>
            <StatusBar
              barStyle="light-content"
              backgroundColor={theme.colors.primary}
              translucent={false}
            />
            <NavigationContainer theme={theme}>
              <Tab.Navigator
                screenOptions={{
                  headerShown: false,
                  tabBarStyle: {
                    backgroundColor: theme.colors.surface,
                    borderTopColor: theme.colors.outline,
                    height: Platform.OS === 'ios' ? 90 : 70,
                    paddingBottom: Platform.OS === 'ios' ? 25 : 10,
                  },
                }}
                tabBar={(props) => <IconTabBar {...props} />}
              >
                <Tab.Screen
                  name="Dashboard"
                  component={DashboardScreen}
                  options={{
                    tabBarIcon: 'view-dashboard',
                    tabBarLabel: 'Dashboard',
                  }}
                />
                <Tab.Screen
                  name="Meetings"
                  component={MeetingScreen}
                  options={{
                    tabBarIcon: 'video',
                    tabBarLabel: 'Meetings',
                  }}
                />
                <Tab.Screen
                  name="Tasks"
                  component={TasksScreen}
                  options={{
                    tabBarIcon: 'checkbox-marked-circle',
                    tabBarLabel: 'Tasks',
                  }}
                />
                <Tab.Screen
                  name="Code"
                  component={CodeScreen}
                  options={{
                    tabBarIcon: 'code-braces',
                    tabBarLabel: 'Code',
                  }}
                />
                <Tab.Screen
                  name="Analytics"
                  component={AnalyticsScreen}
                  options={{
                    tabBarIcon: 'chart-line',
                    tabBarLabel: 'Analytics',
                  }}
                />
                <Tab.Screen
                  name="Settings"
                  component={SettingsScreen}
                  options={{
                    tabBarIcon: 'cog',
                    tabBarLabel: 'Settings',
                  }}
                />
              </Tab.Navigator>
            </NavigationContainer>
          </PaperProvider>
        </PersistGate>
      </Provider>
    );
  }
}

export default App;
