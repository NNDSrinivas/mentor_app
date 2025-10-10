/**
 * Dashboard Screen - Main overview screen with intelligent insights
 * Displays real-time status, upcoming events, and AI-powered recommendations
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Dimensions,
  Alert,
  StatusBar,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Button,
  Surface,
  Chip,
  Avatar,
  ProgressBar,
  Badge,
  IconButton,
} from 'react-native-paper';
import LinearGradient from 'react-native-linear-gradient';

// Services
import { AIService } from '../services/AIService';
import { SyncService } from '../services/SyncService';
import { CalendarService } from '../services/CalendarService';
import { NotificationService } from '../services/NotificationService';
import { OfflineService } from '../services/OfflineService';

// Components
import MetricCard from '../components/MetricCard';
import TaskQuickView from '../components/TaskQuickView';
import MeetingPreview from '../components/MeetingPreview';
import AIInsightCard from '../components/AIInsightCard';
import StatusIndicator from '../components/StatusIndicator';

const { width } = Dimensions.get('window');

interface DashboardData {
  metrics: {
    todaysMeetings: number;
    activeTasks: number;
    codeReviews: number;
    aiInsights: number;
    productivity: number;
    focus: number;
  };
  upcomingMeetings: any[];
  recentTasks: any[];
  aiInsights: any[];
  syncStatus: any;
  offlineStatus: any;
}

const DashboardScreen: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'offline' | 'syncing'>('online');

  // Services
  const [aiService] = useState(() => new AIService());
  const [syncService] = useState(() => new SyncService());
  const [calendarService] = useState(() => new CalendarService());
  const [notificationService] = useState(() => new NotificationService());
  const [offlineService] = useState(() => new OfflineService());

  useEffect(() => {
    initializeDashboard();
  }, []);

  const initializeDashboard = useCallback(async () => {
    try {
      setLoading(true);
      
      // Initialize services if not already done
      await Promise.all([
        aiService.initialize().catch(err => console.warn('AI Service init warning:', err)),
        syncService.initialize().catch(err => console.warn('Sync Service init warning:', err)),
        calendarService.initialize().catch(err => console.warn('Calendar Service init warning:', err)),
        notificationService.initialize().catch(err => console.warn('Notification Service init warning:', err)),
        offlineService.initialize().catch(err => console.warn('Offline Service init warning:', err)),
      ]);

      // Load dashboard data
      await loadDashboardData();
    } catch (error) {
      console.error('Dashboard initialization error:', error);
      Alert.alert('Error', 'Failed to initialize dashboard. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDashboardData = useCallback(async () => {
    try {
      // Check connection status
      updateConnectionStatus();

      // Load data in parallel
      const [
        metrics,
        upcomingMeetings,
        recentTasks,
        aiInsights,
        syncStatus,
        offlineStatus,
      ] = await Promise.all([
        loadMetrics(),
        loadUpcomingMeetings(),
        loadRecentTasks(),
        loadAIInsights(),
        loadSyncStatus(),
        loadOfflineStatus(),
      ]);

      setData({
        metrics,
        upcomingMeetings,
        recentTasks,
        aiInsights,
        syncStatus,
        offlineStatus,
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  }, []);

  const updateConnectionStatus = useCallback(() => {
    const isConnected = aiService.getConnectionStatus();
    const isSyncing = syncService.getPendingItemsCount() > 0;
    
    if (isSyncing) {
      setConnectionStatus('syncing');
    } else if (isConnected) {
      setConnectionStatus('online');
    } else {
      setConnectionStatus('offline');
    }
  }, []);

  const loadMetrics = async () => {
    try {
      // Get today's meetings
      const today = new Date();
      const todaysMeetings = calendarService.getEventsForDay(today);
      
      // Get active tasks (from AsyncStorage or offline storage)
      const activeTasks = await offlineService.queryData('task');
      const pendingTasks = activeTasks.filter(task => task.data?.status !== 'completed');
      
      // Get code reviews
      const codeReviews = await offlineService.queryData('code');
      const pendingReviews = codeReviews.filter(review => review.data?.status === 'pending');
      
      // Get AI insights
      const insights = await offlineService.queryData('ai_response');
      const recentInsights = insights.filter(insight => {
        const age = Date.now() - insight.lastModified.getTime();
        return age < 24 * 60 * 60 * 1000; // Last 24 hours
      });
      
      // Calculate productivity score
      const productivity = calculateProductivityScore(todaysMeetings, pendingTasks, pendingReviews);
      
      // Calculate focus score from calendar insights
      const calendarInsights = calendarService.getCalendarInsights(1); // Today
      const focus = Math.round(calendarInsights.efficiency);

      return {
        todaysMeetings: todaysMeetings.length,
        activeTasks: pendingTasks.length,
        codeReviews: pendingReviews.length,
        aiInsights: recentInsights.length,
        productivity,
        focus,
      };
    } catch (error) {
      console.error('Metrics loading error:', error);
      return {
        todaysMeetings: 0,
        activeTasks: 0,
        codeReviews: 0,
        aiInsights: 0,
        productivity: 0,
        focus: 0,
      };
    }
  };

  const loadUpcomingMeetings = async () => {
    try {
      return calendarService.getUpcomingEvents(8); // Next 8 hours
    } catch (error) {
      console.error('Upcoming meetings loading error:', error);
      return [];
    }
  };

  const loadRecentTasks = async () => {
    try {
      const tasks = await offlineService.queryData('task', undefined, 5);
      return tasks.map(task => task.data);
    } catch (error) {
      console.error('Recent tasks loading error:', error);
      return [];
    }
  };

  const loadAIInsights = async () => {
    try {
      const insights = await offlineService.queryData('ai_response', 'high', 3);
      return insights.map(insight => ({
        ...insight.data,
        timestamp: insight.lastModified,
      }));
    } catch (error) {
      console.error('AI insights loading error:', error);
      return [];
    }
  };

  const loadSyncStatus = async () => {
    try {
      return {
        pendingItems: syncService.getPendingItemsCount(),
        failedItems: syncService.getFailedItemsCount(),
        lastSync: await syncService.getSyncStatus(),
      };
    } catch (error) {
      console.error('Sync status loading error:', error);
      return { pendingItems: 0, failedItems: 0, lastSync: null };
    }
  };

  const loadOfflineStatus = async () => {
    try {
      return offlineService.getState();
    } catch (error) {
      console.error('Offline status loading error:', error);
      return { storageUsed: 0, dataCount: 0, cacheHitRate: 0 };
    }
  };

  const calculateProductivityScore = (meetings: any[], tasks: any[], reviews: any[]): number => {
    // Simple productivity calculation
    let score = 70; // Base score
    
    // Adjust based on meetings (too many reduce productivity)
    if (meetings.length > 4) {
      score -= (meetings.length - 4) * 5;
    }
    
    // Adjust based on completed tasks
    const completedTasks = tasks.filter(task => task.status === 'completed').length;
    score += completedTasks * 5;
    
    // Adjust based on pending reviews
    score -= reviews.length * 3;
    
    return Math.max(0, Math.min(100, score));
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadDashboardData();
    } catch (error) {
      console.error('Refresh error:', error);
    } finally {
      setRefreshing(false);
    }
  }, [loadDashboardData]);

  const handleQuickAction = async (action: string) => {
    try {
      switch (action) {
        case 'start_meeting':
          // Navigate to meeting screen or start quick meeting
          Alert.alert('Quick Meeting', 'Start meeting functionality');
          break;
        case 'create_task':
          // Navigate to task creation
          Alert.alert('Quick Task', 'Create task functionality');
          break;
        case 'ai_assist':
          // Trigger AI assistance
          const response = await aiService.processRequest({
            context: { action: 'dashboard_assist' },
            type: 'general',
            priority: 'medium',
            timestamp: Date.now(),
          });
          Alert.alert('AI Assistant', response.response);
          break;
        case 'sync_now':
          setConnectionStatus('syncing');
          await syncService.performQuickSync();
          await loadDashboardData();
          break;
      }
    } catch (error) {
      console.error('Quick action error:', error);
      Alert.alert('Error', 'Failed to perform action');
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ProgressBar indeterminate color="#6200ea" />
        <Paragraph style={styles.loadingText}>Loading dashboard...</Paragraph>
      </View>
    );
  }

  if (!data) {
    return (
      <View style={styles.errorContainer}>
        <Paragraph>Failed to load dashboard data</Paragraph>
        <Button mode="outlined" onPress={initializeDashboard}>
          Retry
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#6200ea" />
      
      {/* Header */}
      <LinearGradient
        colors={['#6200ea', '#3700b3']}
        style={styles.header}
      >
        <View style={styles.headerContent}>
          <View>
            <Title style={styles.headerTitle}>AI SDLC Assistant</Title>
            <Paragraph style={styles.headerSubtitle}>
              {new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </Paragraph>
          </View>
          <View style={styles.headerActions}>
            <StatusIndicator status={connectionStatus} />
            <IconButton
              icon="refresh"
              iconColor="#fff"
              size={24}
              onPress={onRefresh}
            />
          </View>
        </View>
      </LinearGradient>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Metrics Overview */}
        <View style={styles.section}>
          <Title style={styles.sectionTitle}>Today's Overview</Title>
          <View style={styles.metricsGrid}>
            <MetricCard
              title="Meetings"
              value={data.metrics.todaysMeetings}
              icon="calendar"
              color="#ff6b6b"
              onPress={() => handleQuickAction('start_meeting')}
            />
            <MetricCard
              title="Active Tasks"
              value={data.metrics.activeTasks}
              icon="checkbox-marked-circle"
              color="#4ecdc4"
              onPress={() => handleQuickAction('create_task')}
            />
            <MetricCard
              title="Code Reviews"
              value={data.metrics.codeReviews}
              icon="code-braces"
              color="#45b7d1"
            />
            <MetricCard
              title="AI Insights"
              value={data.metrics.aiInsights}
              icon="brain"
              color="#96ceb4"
              onPress={() => handleQuickAction('ai_assist')}
            />
          </View>
        </View>

        {/* Productivity Metrics */}
        <View style={styles.section}>
          <Title style={styles.sectionTitle}>Productivity</Title>
          <Card style={styles.productivityCard}>
            <Card.Content>
              <View style={styles.productivityRow}>
                <View style={styles.productivityMetric}>
                  <Paragraph style={styles.metricLabel}>Productivity</Paragraph>
                  <View style={styles.progressContainer}>
                    <ProgressBar 
                      progress={data.metrics.productivity / 100} 
                      color="#4caf50"
                      style={styles.progressBar}
                    />
                    <Paragraph style={styles.progressText}>
                      {data.metrics.productivity}%
                    </Paragraph>
                  </View>
                </View>
                <View style={styles.productivityMetric}>
                  <Paragraph style={styles.metricLabel}>Focus Time</Paragraph>
                  <View style={styles.progressContainer}>
                    <ProgressBar 
                      progress={data.metrics.focus / 100} 
                      color="#2196f3"
                      style={styles.progressBar}
                    />
                    <Paragraph style={styles.progressText}>
                      {data.metrics.focus}%
                    </Paragraph>
                  </View>
                </View>
              </View>
            </Card.Content>
          </Card>
        </View>

        {/* Upcoming Meetings */}
        {data.upcomingMeetings.length > 0 && (
          <View style={styles.section}>
            <Title style={styles.sectionTitle}>Upcoming Meetings</Title>
            {data.upcomingMeetings.slice(0, 3).map((meeting, index) => (
              <MeetingPreview
                key={meeting.id || index}
                meeting={meeting}
                onPress={() => {/* Navigate to meeting details */}}
              />
            ))}
          </View>
        )}

        {/* AI Insights */}
        {data.aiInsights.length > 0 && (
          <View style={styles.section}>
            <Title style={styles.sectionTitle}>AI Insights</Title>
            {data.aiInsights.map((insight, index) => (
              <AIInsightCard
                key={insight.id || index}
                insight={insight}
                onAction={(action) => handleQuickAction(action)}
              />
            ))}
          </View>
        )}

        {/* Recent Tasks */}
        {data.recentTasks.length > 0 && (
          <View style={styles.section}>
            <Title style={styles.sectionTitle}>Recent Tasks</Title>
            <TaskQuickView
              tasks={data.recentTasks.slice(0, 5)}
              onTaskPress={(task) => {/* Navigate to task details */}}
            />
          </View>
        )}

        {/* System Status */}
        <View style={styles.section}>
          <Title style={styles.sectionTitle}>System Status</Title>
          <Card style={styles.statusCard}>
            <Card.Content>
              <View style={styles.statusRow}>
                <Chip
                  icon="sync"
                  mode="outlined"
                  style={[
                    styles.statusChip,
                    { borderColor: data.syncStatus.pendingItems > 0 ? '#ff9800' : '#4caf50' }
                  ]}
                >
                  Sync: {data.syncStatus.pendingItems} pending
                </Chip>
                <Chip
                  icon="database"
                  mode="outlined"
                  style={[styles.statusChip, { borderColor: '#2196f3' }]}
                >
                  Storage: {Math.round(data.offlineStatus.storageUsed / 1024 / 1024)}MB
                </Chip>
              </View>
              <View style={styles.statusRow}>
                <Chip
                  icon="cached"
                  mode="outlined"
                  style={[styles.statusChip, { borderColor: '#9c27b0' }]}
                >
                  Cache: {Math.round(data.offlineStatus.cacheHitRate)}%
                </Chip>
                <Button
                  mode="contained"
                  icon="sync"
                  size="small"
                  onPress={() => handleQuickAction('sync_now')}
                  disabled={connectionStatus === 'syncing'}
                >
                  {connectionStatus === 'syncing' ? 'Syncing...' : 'Sync Now'}
                </Button>
              </View>
            </Card.Content>
          </Card>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Title style={styles.sectionTitle}>Quick Actions</Title>
          <View style={styles.quickActions}>
            <Button
              mode="contained"
              icon="video"
              onPress={() => handleQuickAction('start_meeting')}
              style={styles.quickActionButton}
            >
              Start Meeting
            </Button>
            <Button
              mode="outlined"
              icon="plus"
              onPress={() => handleQuickAction('create_task')}
              style={styles.quickActionButton}
            >
              Create Task
            </Button>
            <Button
              mode="outlined"
              icon="robot"
              onPress={() => handleQuickAction('ai_assist')}
              style={styles.quickActionButton}
            >
              AI Assist
            </Button>
          </View>
        </View>

        <View style={styles.bottomSpacing} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  header: {
    paddingTop: 20,
    paddingBottom: 20,
    paddingHorizontal: 16,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: '#e8eaf6',
    fontSize: 14,
    marginTop: 4,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  productivityCard: {
    marginBottom: 8,
  },
  productivityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  productivityMetric: {
    flex: 1,
    marginHorizontal: 8,
  },
  metricLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressBar: {
    flex: 1,
    height: 6,
    borderRadius: 3,
  },
  progressText: {
    marginLeft: 8,
    fontSize: 12,
    fontWeight: '600',
    minWidth: 35,
  },
  statusCard: {
    marginBottom: 8,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusChip: {
    marginRight: 8,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  quickActionButton: {
    width: '48%',
    marginBottom: 8,
  },
  bottomSpacing: {
    height: 20,
  },
});

export default DashboardScreen;
