/**
 * Meeting Screen - Comprehensive meeting management interface
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
} from 'react-native';
import {
  Appbar,
  Searchbar,
  FAB,
  Chip,
  Button,
  Title,
  Paragraph,
  Surface,
  Portal,
  Modal,
  SegmentedButtons,
} from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';

import { MeetingPreview, StatusIndicator } from '../components';
import type { MeetingData } from '../components/MeetingPreview';
import type { RootState } from '../store';
import {
  setMeetings,
  setSearchQuery,
  setSelectedMeeting,
  setLoading,
  generatePreparationTasks,
} from '../store/slices/meetingsSlice';

const MeetingScreen: React.FC = () => {
  const dispatch = useDispatch();
  const {
    upcomingMeetings,
    pastMeetings,
    currentMeeting,
    searchQuery,
    loading,
    preparationReminders,
  } = useSelector((state: RootState) => state.meetings);

  const [activeTab, setActiveTab] = useState('upcoming');
  const [showPrepModal, setShowPrepModal] = useState(false);
  const [selectedMeeting, setSelectedMeetingLocal] = useState<MeetingData | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      loadMeetings();
    }, [])
  );

  const loadMeetings = async () => {
    dispatch(setLoading(true));
    try {
      // Simulate API call to load meetings
      const mockMeetings: MeetingData[] = [
        {
          id: '1',
          title: 'Sprint Planning',
          description: 'Plan upcoming sprint goals and backlog items',
          startTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
          endTime: new Date(Date.now() + 3 * 60 * 60 * 1000),
          attendees: [
            { name: 'John Doe', email: 'john@example.com', status: 'accepted' },
            { name: 'Jane Smith', email: 'jane@example.com', status: 'pending' },
          ],
          preparationStatus: {
            isComplete: false,
            completedItems: 2,
            totalItems: 5,
            suggestions: [
              'Review backlog items',
              'Prepare velocity metrics',
              'Check team availability',
              'Prepare sprint goals',
              'Review previous sprint retrospective',
            ],
          },
          aiInsights: {
            meetingType: 'planning',
            suggestedDuration: 60,
            keyTopics: ['Backlog', 'Velocity', 'Goals'],
            preparationScore: 0.6,
          },
          priority: 'high',
          isRecurring: true,
        },
        {
          id: '2',
          title: 'Code Review Session',
          description: 'Review recent pull requests and discuss best practices',
          startTime: new Date(Date.now() + 24 * 60 * 60 * 1000), // Tomorrow
          endTime: new Date(Date.now() + 25 * 60 * 60 * 1000),
          meetingUrl: 'https://meet.google.com/abc-defg-hij',
          attendees: [
            { name: 'Alice Johnson', email: 'alice@example.com', status: 'accepted' },
            { name: 'Bob Wilson', email: 'bob@example.com', status: 'accepted' },
          ],
          preparationStatus: {
            isComplete: true,
            completedItems: 3,
            totalItems: 3,
            suggestions: [
              'Review assigned PRs',
              'Prepare feedback notes',
              'Check code quality metrics',
            ],
          },
          aiInsights: {
            meetingType: 'review',
            suggestedDuration: 45,
            keyTopics: ['Code Quality', 'Best Practices', 'PRs'],
            preparationScore: 1.0,
          },
          priority: 'medium',
        },
      ];

      dispatch(setMeetings(mockMeetings));
    } catch (error) {
      console.error('Error loading meetings:', error);
      Alert.alert('Error', 'Failed to load meetings');
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadMeetings();
    setRefreshing(false);
  };

  const handleMeetingPress = (meeting: MeetingData) => {
    setSelectedMeetingLocal(meeting);
    dispatch(setSelectedMeeting(meeting.id));
    // Navigate to meeting details
  };

  const handlePreparePress = (meeting: MeetingData) => {
    setSelectedMeetingLocal(meeting);
    setShowPrepModal(true);
    dispatch(generatePreparationTasks(meeting.id));
  };

  const handleJoinPress = (meeting: MeetingData) => {
    if (meeting.meetingUrl) {
      // Open meeting URL
      Alert.alert(
        'Join Meeting',
        `Would you like to join "${meeting.title}"?`,
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Join', onPress: () => console.log('Joining meeting:', meeting.meetingUrl) },
        ]
      );
    }
  };

  const renderMeetingList = (meetings: MeetingData[]) => {
    if (meetings.length === 0) {
      return (
        <Surface style={styles.emptyState}>
          <Title>No meetings found</Title>
          <Paragraph>
            {activeTab === 'upcoming' 
              ? 'You have no upcoming meetings.' 
              : 'No past meetings to display.'}
          </Paragraph>
        </Surface>
      );
    }

    return meetings.map((meeting) => (
      <MeetingPreview
        key={meeting.id}
        meeting={meeting}
        onPress={() => handleMeetingPress(meeting)}
        onPrepare={() => handlePreparePress(meeting)}
        onJoin={() => handleJoinPress(meeting)}
        showActions={true}
      />
    ));
  };

  const getFilteredMeetings = () => {
    const meetings = activeTab === 'upcoming' ? upcomingMeetings : pastMeetings;
    
    if (!searchQuery) return meetings;
    
    return meetings.filter(meeting =>
      meeting.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      meeting.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      meeting.attendees.some(attendee =>
        attendee.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.Content title="Meetings" />
        <Appbar.Action icon="calendar-plus" onPress={() => {}} />
        <Appbar.Action icon="filter-variant" onPress={() => {}} />
      </Appbar.Header>

      <View style={styles.content}>
        {/* Search Bar */}
        <Searchbar
          placeholder="Search meetings..."
          onChangeText={(query) => dispatch(setSearchQuery(query))}
          value={searchQuery}
          style={styles.searchbar}
        />

        {/* Tab Navigation */}
        <SegmentedButtons
          value={activeTab}
          onValueChange={setActiveTab}
          buttons={[
            { value: 'upcoming', label: `Upcoming (${upcomingMeetings.length})` },
            { value: 'past', label: `Past (${pastMeetings.length})` },
          ]}
          style={styles.tabs}
        />

        {/* Current Meeting Alert */}
        {currentMeeting && (
          <Surface style={styles.currentMeetingAlert}>
            <Title style={styles.currentMeetingTitle}>Meeting in Progress</Title>
            <Paragraph>{currentMeeting.title}</Paragraph>
            <Button
              mode="contained"
              onPress={() => handleJoinPress(currentMeeting)}
              style={styles.joinButton}
            >
              Rejoin Meeting
            </Button>
          </Surface>
        )}

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <Chip
            icon="clock-outline"
            onPress={() => setActiveTab('upcoming')}
            selected={activeTab === 'upcoming'}
            style={styles.actionChip}
          >
            Today's Meetings
          </Chip>
          <Chip
            icon="preparation"
            onPress={() => {}}
            style={styles.actionChip}
          >
            Need Preparation
          </Chip>
          <Chip
            icon="video"
            onPress={() => {}}
            style={styles.actionChip}
          >
            Online Meetings
          </Chip>
        </View>

        {/* Meeting List */}
        <ScrollView
          style={styles.meetingList}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          {renderMeetingList(getFilteredMeetings())}
        </ScrollView>
      </View>

      {/* Floating Action Button */}
      <FAB
        style={styles.fab}
        icon="plus"
        onPress={() => {}}
        label="New Meeting"
      />

      {/* Preparation Modal */}
      <Portal>
        <Modal
          visible={showPrepModal}
          onDismiss={() => setShowPrepModal(false)}
          contentContainerStyle={styles.modalContent}
        >
          {selectedMeeting && (
            <>
              <Title>Meeting Preparation</Title>
              <Paragraph style={styles.modalSubtitle}>
                {selectedMeeting.title}
              </Paragraph>
              
              <View style={styles.preparationList}>
                {selectedMeeting.preparationStatus.suggestions.map((suggestion, index) => (
                  <View key={index} style={styles.preparationItem}>
                    <Chip
                      mode="outlined"
                      icon={index < selectedMeeting.preparationStatus.completedItems ? 'check' : 'circle-outline'}
                      onPress={() => {}}
                      style={styles.preparationChip}
                    >
                      {suggestion}
                    </Chip>
                  </View>
                ))}
              </View>

              <View style={styles.modalActions}>
                <Button onPress={() => setShowPrepModal(false)}>
                  Close
                </Button>
                <Button mode="contained" onPress={() => setShowPrepModal(false)}>
                  Mark Complete
                </Button>
              </View>
            </>
          )}
        </Modal>
      </Portal>

      {/* Status Indicator */}
      <StatusIndicator
        status={{
          connection: {
            status: 'connected',
            quality: 'excellent',
            latency: 45,
            lastSync: new Date(),
          },
          services: {
            ai: 'online',
            sync: 'active',
            notifications: 'enabled',
            calendar: 'connected',
            offline: 'ready',
          },
        }}
        compact={true}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  searchbar: {
    marginBottom: 16,
    elevation: 2,
  },
  tabs: {
    marginBottom: 16,
  },
  currentMeetingAlert: {
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#FF5722',
    elevation: 4,
  },
  currentMeetingTitle: {
    color: '#FF5722',
    fontSize: 16,
    marginBottom: 4,
  },
  joinButton: {
    marginTop: 8,
    backgroundColor: '#FF5722',
  },
  quickActions: {
    flexDirection: 'row',
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  actionChip: {
    marginRight: 8,
    marginBottom: 8,
  },
  meetingList: {
    flex: 1,
  },
  emptyState: {
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
  },
  fab: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    backgroundColor: '#6200ea',
  },
  modalContent: {
    backgroundColor: 'white',
    padding: 20,
    margin: 20,
    borderRadius: 8,
    maxHeight: '80%',
  },
  modalSubtitle: {
    opacity: 0.7,
    marginBottom: 16,
  },
  preparationList: {
    marginBottom: 20,
  },
  preparationItem: {
    marginBottom: 8,
  },
  preparationChip: {
    alignSelf: 'flex-start',
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});

export default MeetingScreen;
