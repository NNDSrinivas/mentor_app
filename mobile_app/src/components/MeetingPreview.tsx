/**
 * Meeting Preview - Displays upcoming meeting information with preparation status
 */

import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Chip,
  Button,
  Avatar,
  ProgressBar,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface MeetingData {
  id: string;
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  location?: string;
  meetingUrl?: string;
  attendees: Array<{
    name: string;
    email: string;
    status: 'accepted' | 'declined' | 'tentative' | 'pending';
  }>;
  preparationStatus: {
    isComplete: boolean;
    completedItems: number;
    totalItems: number;
    suggestions: string[];
  };
  aiInsights?: {
    meetingType: 'standup' | 'planning' | 'review' | 'interview' | 'other';
    suggestedDuration: number;
    keyTopics: string[];
    preparationScore: number;
  };
  isRecurring?: boolean;
  priority: 'low' | 'medium' | 'high';
}

interface MeetingPreviewProps {
  meeting: MeetingData;
  onPress?: () => void;
  onPrepare?: () => void;
  onJoin?: () => void;
  showActions?: boolean;
  compact?: boolean;
}

const MeetingPreview: React.FC<MeetingPreviewProps> = ({
  meeting,
  onPress,
  onPrepare,
  onJoin,
  showActions = true,
  compact = false,
}) => {
  const formatTime = () => {
    const start = new Date(meeting.startTime);
    const end = new Date(meeting.endTime);
    const startTime = start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const endTime = end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `${startTime} - ${endTime}`;
  };

  const getTimeUntilMeeting = () => {
    const now = new Date();
    const start = new Date(meeting.startTime);
    const diffMinutes = Math.round((start.getTime() - now.getTime()) / (1000 * 60));
    
    if (diffMinutes < 0) return 'In progress';
    if (diffMinutes < 60) return `In ${diffMinutes}m`;
    if (diffMinutes < 1440) return `In ${Math.round(diffMinutes / 60)}h`;
    return `In ${Math.round(diffMinutes / 1440)}d`;
  };

  const getPriorityColor = () => {
    switch (meeting.priority) {
      case 'high':
        return '#F44336';
      case 'medium':
        return '#FF9800';
      default:
        return '#4CAF50';
    }
  };

  const getMeetingTypeIcon = () => {
    if (!meeting.aiInsights) return 'calendar';
    
    switch (meeting.aiInsights.meetingType) {
      case 'standup':
        return 'account-group';
      case 'planning':
        return 'clipboard-text';
      case 'review':
        return 'eye';
      case 'interview':
        return 'account-question';
      default:
        return 'calendar';
    }
  };

  const getPreparationColor = () => {
    const { preparationStatus } = meeting;
    if (preparationStatus.isComplete) return '#4CAF50';
    if (preparationStatus.completedItems > 0) return '#FF9800';
    return '#F44336';
  };

  const isStartingSoon = () => {
    const now = new Date();
    const start = new Date(meeting.startTime);
    const diffMinutes = (start.getTime() - now.getTime()) / (1000 * 60);
    return diffMinutes <= 15 && diffMinutes > 0;
  };

  const timeUntil = getTimeUntilMeeting();
  const preparationProgress = meeting.preparationStatus.completedItems / meeting.preparationStatus.totalItems;

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <Card style={[
        styles.card, 
        compact && styles.cardCompact,
        isStartingSoon() && styles.cardUrgent
      ]}>
        <Card.Content style={[styles.content, compact && styles.contentCompact]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.iconContainer}>
              <Avatar.Icon
                size={compact ? 32 : 40}
                icon={getMeetingTypeIcon()}
                style={[styles.meetingIcon, { backgroundColor: getPriorityColor() }]}
              />
              {meeting.isRecurring && (
                <Icon
                  name="repeat"
                  size={12}
                  color="#757575"
                  style={styles.recurringIcon}
                />
              )}
            </View>

            <View style={styles.titleContainer}>
              <Title style={[styles.title, compact && styles.titleCompact]}>
                {meeting.title}
              </Title>
              <View style={styles.timeContainer}>
                <Icon name="clock-outline" size={14} color="#757575" />
                <Paragraph style={styles.timeText}>{formatTime()}</Paragraph>
                <Chip
                  mode="outlined"
                  compact
                  style={[styles.timeChip, { borderColor: getPriorityColor() }]}
                  textStyle={{ color: getPriorityColor(), fontSize: 10 }}
                >
                  {timeUntil}
                </Chip>
              </View>
            </View>
          </View>

          {/* Meeting Details */}
          {!compact && (
            <>
              {meeting.description && (
                <Paragraph style={styles.description} numberOfLines={2}>
                  {meeting.description}
                </Paragraph>
              )}

              {meeting.location && (
                <View style={styles.locationContainer}>
                  <Icon name="map-marker" size={14} color="#757575" />
                  <Paragraph style={styles.locationText}>{meeting.location}</Paragraph>
                </View>
              )}
            </>
          )}

          {/* Attendees */}
          <View style={styles.attendeesContainer}>
            <View style={styles.attendeeAvatars}>
              {meeting.attendees.slice(0, 3).map((attendee, index) => (
                <Avatar.Text
                  key={index}
                  size={24}
                  label={attendee.name.split(' ').map(n => n[0]).join('')}
                  style={[styles.attendeeAvatar, { zIndex: 3 - index }]}
                />
              ))}
              {meeting.attendees.length > 3 && (
                <Paragraph style={styles.moreAttendeesText}>
                  +{meeting.attendees.length - 3}
                </Paragraph>
              )}
            </View>
          </View>

          {/* Preparation Status */}
          <View style={styles.preparationContainer}>
            <View style={styles.preparationHeader}>
              <Icon
                name="clipboard-check"
                size={16}
                color={getPreparationColor()}
              />
              <Paragraph style={styles.preparationLabel}>Preparation</Paragraph>
              <Paragraph style={[styles.preparationScore, { color: getPreparationColor() }]}>
                {meeting.preparationStatus.completedItems}/{meeting.preparationStatus.totalItems}
              </Paragraph>
            </View>
            <ProgressBar
              progress={preparationProgress}
              color={getPreparationColor()}
              style={styles.preparationProgress}
            />
          </View>

          {/* AI Insights */}
          {!compact && meeting.aiInsights && (
            <View style={styles.insightsContainer}>
              <View style={styles.insightsHeader}>
                <Icon name="brain" size={14} color="#9C27B0" />
                <Paragraph style={styles.insightsLabel}>AI Insights</Paragraph>
              </View>
              <View style={styles.keyTopics}>
                {meeting.aiInsights.keyTopics.slice(0, 2).map((topic, index) => (
                  <Chip
                    key={index}
                    mode="flat"
                    compact
                    style={styles.topicChip}
                    textStyle={styles.topicText}
                  >
                    {topic}
                  </Chip>
                ))}
              </View>
            </View>
          )}

          {/* Actions */}
          {showActions && (
            <View style={styles.actions}>
              {!meeting.preparationStatus.isComplete && onPrepare && (
                <Button
                  mode="outlined"
                  compact
                  onPress={onPrepare}
                  style={styles.actionButton}
                  labelStyle={styles.actionButtonText}
                >
                  Prepare
                </Button>
              )}
              {meeting.meetingUrl && onJoin && isStartingSoon() && (
                <Button
                  mode="contained"
                  compact
                  onPress={onJoin}
                  style={[styles.actionButton, styles.joinButton]}
                  labelStyle={styles.actionButtonText}
                >
                  Join
                </Button>
              )}
            </View>
          )}
        </Card.Content>
      </Card>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    margin: 8,
    elevation: 2,
    borderRadius: 12,
  },
  cardCompact: {
    margin: 4,
  },
  cardUrgent: {
    borderLeftWidth: 4,
    borderLeftColor: '#FF5722',
  },
  content: {
    padding: 16,
  },
  contentCompact: {
    padding: 12,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  iconContainer: {
    position: 'relative',
    marginRight: 12,
  },
  meetingIcon: {
    borderRadius: 8,
  },
  recurringIcon: {
    position: 'absolute',
    top: -2,
    right: -2,
    backgroundColor: '#ffffff',
    borderRadius: 6,
    padding: 1,
  },
  titleContainer: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  titleCompact: {
    fontSize: 14,
  },
  timeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  timeText: {
    fontSize: 12,
    marginLeft: 4,
    marginRight: 8,
    opacity: 0.7,
  },
  timeChip: {
    height: 20,
  },
  description: {
    fontSize: 12,
    opacity: 0.7,
    marginBottom: 8,
    lineHeight: 16,
  },
  locationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  locationText: {
    fontSize: 12,
    marginLeft: 4,
    opacity: 0.7,
  },
  attendeesContainer: {
    marginBottom: 12,
  },
  attendeeAvatars: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  attendeeAvatar: {
    marginRight: -8,
    borderWidth: 1,
    borderColor: '#ffffff',
  },
  moreAttendeesText: {
    fontSize: 12,
    marginLeft: 16,
    opacity: 0.7,
  },
  preparationContainer: {
    marginBottom: 12,
  },
  preparationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  preparationLabel: {
    fontSize: 12,
    marginLeft: 4,
    flex: 1,
    opacity: 0.8,
  },
  preparationScore: {
    fontSize: 12,
    fontWeight: '600',
  },
  preparationProgress: {
    height: 4,
    borderRadius: 2,
  },
  insightsContainer: {
    marginBottom: 12,
  },
  insightsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  insightsLabel: {
    fontSize: 12,
    marginLeft: 4,
    opacity: 0.8,
  },
  keyTopics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  topicChip: {
    marginRight: 4,
    marginBottom: 4,
    backgroundColor: 'rgba(156, 39, 176, 0.1)',
    height: 24,
  },
  topicText: {
    fontSize: 10,
    color: '#9C27B0',
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  actionButton: {
    marginLeft: 8,
  },
  joinButton: {
    backgroundColor: '#4CAF50',
  },
  actionButtonText: {
    fontSize: 12,
  },
});

export default MeetingPreview;
