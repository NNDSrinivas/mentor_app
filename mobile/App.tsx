// mobile/App.tsx

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  Alert,
  StatusBar,
  TextInput,
  RefreshControl,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';

const Stack = createStackNavigator();

interface Answer {
  id?: string;
  question: string;
  answer: string;
  timestamp?: string; // allow missing timestamp safely
  userLevel: string;
  memoryContextUsed?: boolean;
}

function HomeScreen({ navigation }: any) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [serverUrl, setServerUrl] = useState('http://192.168.1.100:8080'); // Default local IP
  const [userLevel, setUserLevel] = useState('IC5');
  const [refreshing, setRefreshing] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const syncIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Auto-connect on app start
    if (!sessionId) {
      startSession();
    }
    // Cleanup on unmount
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    };
  }, []);

  // Helper to normalize and guard base URL
  const normalizeBaseUrl = (url: string) => {
    const trimmed = url.trim().replace(/\/+$/, '');
    if (!/^https?:\/\//i.test(trimmed)) return `http://${trimmed}`;
    return trimmed;
  };

  const startSession = async () => {
    try {
      const base = normalizeBaseUrl(serverUrl);
      const response = await fetch(`${base}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_level: userLevel,
          meeting_type: 'technical_interview',
          user_name: 'mobile_user'
        })
      });

      if (!response.ok) throw new Error(`Failed to create session (${response.status})`);

      const data = await response.json();
      const newSessionId = data.session_id || data.id || data.sessionId;
      if (!newSessionId) throw new Error('Server did not return a session id');

      setSessionId(newSessionId);
      setIsConnected(true);

      // Start polling for answers
      startPolling(newSessionId, base);
      startSessionSync(newSessionId, base);

      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert('Connected', 'AI Interview Assistant is ready');

    } catch (error) {
      console.error('Failed to start session:', error);
      setIsConnected(false);
      Alert.alert('Connection Failed', 'Please check your server URL and try again');
    }
  };

  // Normalize backend answer shape (snake_case) to app's camelCase Answer
  const normalizeAnswer = useCallback((raw: any, idx: number): Answer => {
    const userLevel = raw?.userLevel || raw?.user_level || 'IC5';
    const memoryContextUsed =
      typeof raw?.memoryContextUsed !== 'undefined'
        ? !!raw.memoryContextUsed
        : !!raw?.memory_context_used;
    const id = raw?.id || `${idx}-${raw?.timestamp || Date.now()}`;
    return {
      id,
      question: raw?.question || '',
      answer: raw?.answer || '',
      timestamp: raw?.timestamp,
      userLevel,
      memoryContextUsed,
    };
  }, []);

  const startPolling = (sid: string, baseUrl?: string) => {
    const base = baseUrl ?? normalizeBaseUrl(serverUrl);

    // Clear any existing poller
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    // Immediate fetch then interval
    const fetchAnswers = async () => {
      try {
        const resp = await fetch(`${base}/api/sessions/${encodeURIComponent(sid)}/answers`);
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data.answers)) {
            setAnswers(data.answers.map((a: any, i: number) => normalizeAnswer(a, i)));
          }
        } else {
          // If server doesn’t have this endpoint, avoid spamming errors
          if (resp.status === 404) {
            console.warn('Answers endpoint not found. Consider using SSE stream per backend docs.');
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    fetchAnswers();
    pollIntervalRef.current = setInterval(fetchAnswers, 3000);
  };

  const startSessionSync = (sid: string, baseUrl?: string) => {
    const base = baseUrl ?? normalizeBaseUrl(serverUrl);

    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }

    const fetchState = async () => {
      try {
        const resp = await fetch(`${base}/api/sessions/${encodeURIComponent(sid)}/sync`);
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data.answers)) {
            setAnswers(data.answers.map((a: any, i: number) => normalizeAnswer(a, i)));
          }
        }
      } catch (e) {
        console.error('Sync error:', e);
      }
    };

    fetchState();
    syncIntervalRef.current = setInterval(fetchState, 5000);
  };

  const broadcastState = async (state: any) => {
    if (!sessionId) return;
    const base = normalizeBaseUrl(serverUrl);
    try {
      await fetch(`${base}/api/sessions/${encodeURIComponent(sessionId)}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state),
      });
    } catch (e) {
      console.error('Broadcast error:', e);
    }
  };

  useEffect(() => {
    if (sessionId) {
      broadcastState({ answers });
    }
  }, [answers]);

  const endSession = async () => {
    const base = normalizeBaseUrl(serverUrl);
    const sid = sessionId;
    if (sid) {
      try {
        await fetch(`${base}/api/sessions/${encodeURIComponent(sid)}`, { method: 'DELETE' });
      } catch (e) {
        // Non-fatal; proceed with local cleanup
        console.warn('Failed to notify server to end session', e);
      }
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }
    setSessionId(null);
    setIsConnected(false);
    setAnswers([]);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    if (sessionId) {
      try {
        const base = normalizeBaseUrl(serverUrl);
        const response = await fetch(`${base}/api/sessions/${encodeURIComponent(sessionId)}/answers`);
        if (response.ok) {
          const data = await response.json();
          setAnswers(Array.isArray(data.answers) ? data.answers.map((a: any, i: number) => normalizeAnswer(a, i)) : []);
        }
      } catch (error) {
        console.error('Refresh error:', error);
      }
    }
    setRefreshing(false);
  };

  const copyAnswer = async (answer: Answer) => {
    await Clipboard.setStringAsync(`Q: ${answer.question}\n\nA: ${answer.answer}`);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    Alert.alert('Copied', 'Answer copied to clipboard');
  };

  const safeTime = useCallback((ts?: string) => {
    try {
      if (!ts) return '';
      const d = new Date(ts);
      return isNaN(d.getTime()) ? '' : d.toLocaleTimeString();
    } catch {
      return '';
    }
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>AI Interview Assistant</Text>
        <View style={[styles.statusIndicator, { backgroundColor: isConnected ? '#4ade80' : '#ef4444' }]} />
      </View>

      {/* Connection Settings */}
      {!isConnected && (
        <View style={styles.settingsSection}>
          <Text style={styles.sectionTitle}>Connection Settings</Text>
          <TextInput
            style={styles.input}
            value={serverUrl}
            onChangeText={setServerUrl}
            placeholder="Server URL (e.g., http://192.168.1.100:8080)"
            placeholderTextColor="#666"
          />
          <View style={styles.levelSelector}>
            {['IC3', 'IC4', 'IC5', 'IC6', 'IC7'].map(level => (
              <TouchableOpacity
                key={level}
                style={[styles.levelButton, userLevel === level && styles.levelButtonActive]}
                onPress={() => setUserLevel(level)}
              >
                <Text style={[styles.levelButtonText, userLevel === level && styles.levelButtonTextActive]}>
                  {level}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={styles.connectButton} onPress={startSession}>
            <Text style={styles.connectButtonText}>Connect</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Session Controls */}
      {isConnected && (
        <View style={styles.controlsSection}>
          <Text style={styles.sectionTitle}>
            Session Active ({answers.length} answers)
          </Text>
          <TouchableOpacity style={styles.endButton} onPress={endSession}>
            <Text style={styles.endButtonText}>End Session</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Answers List */}
      <ScrollView
        style={styles.answersList}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#667eea" />
        }
      >
        {answers.length === 0 ? (
          <Text style={styles.emptyText}>
            {isConnected ? 'Waiting for questions...' : 'Not connected'}
          </Text>
        ) : (
          answers.map((answer, index) => (
            <TouchableOpacity
              key={answer.id || index}
              style={styles.answerCard}
              onPress={() => navigation.navigate('AnswerDetail', { answer })}
              onLongPress={() => copyAnswer(answer)}
            >
              <View style={styles.answerHeader}>
                <Text style={styles.answerIndex}>#{answers.length - index}</Text>
                <Text style={styles.answerLevel}>{answer.userLevel}</Text>
                {answer.memoryContextUsed && (
                  <View style={styles.contextBadge}>
                    <Text style={styles.contextBadgeText}>📚</Text>
                  </View>
                )}
              </View>
              <Text style={styles.answerQuestion} numberOfLines={2}>
                {answer.question}
              </Text>
              <Text style={styles.answerPreview} numberOfLines={3}>
                {answer.answer}
              </Text>
              <Text style={styles.answerTime}>
                {safeTime(answer.timestamp)}
              </Text>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

function AnswerDetailScreen({ route }: any) {
  const { answer } = route.params;

  const copyFullAnswer = async () => {
    await Clipboard.setStringAsync(`Q: ${answer.question}\n\nA: ${answer.answer}`);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    Alert.alert('Copied', 'Full answer copied to clipboard');
  };

  const copyAnswerOnly = async () => {
    await Clipboard.setStringAsync(answer.answer);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    Alert.alert('Copied', 'Answer copied to clipboard');
  };

  const detailTime = (() => {
    try {
      if (!answer.timestamp) return '';
      const d = new Date(answer.timestamp);
      return isNaN(d.getTime()) ? '' : d.toLocaleString();
    } catch {
      return '';
    }
  })();

  return (
    <View style={styles.container}>
      <ScrollView style={styles.detailContainer}>
        <View style={styles.detailHeader}>
          <Text style={styles.detailLevel}>{answer.userLevel}</Text>
          <Text style={styles.detailTime}>
            {detailTime}
          </Text>
          {answer.memoryContextUsed && (
            <Text style={styles.contextIndicator}>📚 Context-aware</Text>
          )}
        </View>

        <View style={styles.questionSection}>
          <Text style={styles.sectionLabel}>QUESTION</Text>
          <Text style={styles.questionText}>{answer.question}</Text>
        </View>

        <View style={styles.answerSection}>
          <Text style={styles.sectionLabel}>SUGGESTED ANSWER</Text>
          <Text style={styles.answerText}>{answer.answer}</Text>
        </View>

        <View style={styles.actionButtons}>
          <TouchableOpacity style={styles.actionButton} onPress={copyAnswerOnly}>
            <Text style={styles.actionButtonText}>Copy Answer</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton} onPress={copyFullAnswer}>
            <Text style={styles.actionButtonText}>Copy All</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
}

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#1a1a1a' },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: '600' }
        }}
      >
        <Stack.Screen 
          name="Home" 
          component={HomeScreen} 
          options={{ headerShown: false }}
        />
        <Stack.Screen 
          name="AnswerDetail" 
          component={AnswerDetailScreen}
          options={{ title: 'Answer Details' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 50,
    backgroundColor: '#2a2a2a',
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#fff',
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  settingsSection: {
    padding: 20,
    backgroundColor: '#2a2a2a',
    margin: 20,
    borderRadius: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 16,
  },
  input: {
    backgroundColor: '#333',
    color: '#fff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    fontSize: 16,
  },
  levelSelector: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  levelButton: {
    flex: 1,
    padding: 8,
    marginHorizontal: 4,
    backgroundColor: '#333',
    borderRadius: 6,
    alignItems: 'center',
  },
  levelButtonActive: {
    backgroundColor: '#667eea',
  },
  levelButtonText: {
    color: '#ccc',
    fontWeight: '500',
  },
  levelButtonTextActive: {
    color: '#fff',
  },
  connectButton: {
    backgroundColor: '#667eea',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  connectButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  controlsSection: {
    padding: 20,
    backgroundColor: '#2a2a2a',
    margin: 20,
    borderRadius: 12,
  },
  endButton: {
    backgroundColor: '#ef4444',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  endButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  answersList: {
    flex: 1,
    padding: 20,
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    fontSize: 16,
    marginTop: 50,
  },
  answerCard: {
    backgroundColor: '#2a2a2a',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#667eea',
  },
  answerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  answerIndex: {
    color: '#667eea',
    fontSize: 14,
    fontWeight: '600',
  },
  answerLevel: {
    color: '#999',
    fontSize: 12,
  },
  contextBadge: {
    backgroundColor: '#333',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  contextBadgeText: {
    fontSize: 12,
  },
  answerQuestion: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
    lineHeight: 22,
  },
  answerPreview: {
    color: '#ccc',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 8,
  },
  answerTime: {
    color: '#666',
    fontSize: 12,
  },
  detailContainer: {
    flex: 1,
    padding: 20,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  detailLevel: {
    color: '#667eea',
    fontSize: 16,
    fontWeight: '600',
  },
  detailTime: {
    color: '#999',
    fontSize: 14,
  },
  contextIndicator: {
    color: '#4ade80',
    fontSize: 12,
  },
  questionSection: {
    marginBottom: 24,
  },
  sectionLabel: {
    color: '#667eea',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
    letterSpacing: 1,
  },
  questionText: {
    color: '#fff',
    fontSize: 16,
    lineHeight: 24,
  },
  answerSection: {
    marginBottom: 24,
  },
  answerText: {
    color: '#ccc',
    fontSize: 16,
    lineHeight: 24,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 24,
  },
  actionButton: {
    backgroundColor: '#333',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: '500',
  },
});
