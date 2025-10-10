/**
 * Task Quick View - Compact display for task items
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
  IconButton,
  Avatar,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface TaskData {
  id: string;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'in_progress' | 'review' | 'completed';
  dueDate?: Date;
  assignee?: string;
  tags?: string[];
  estimatedTime?: number; // minutes
  actualTime?: number; // minutes
  type: 'bug' | 'feature' | 'task' | 'improvement';
}

interface TaskQuickViewProps {
  task: TaskData;
  onPress?: () => void;
  onStatusChange?: (taskId: string, newStatus: TaskData['status']) => void;
  showActions?: boolean;
  compact?: boolean;
}

const TaskQuickView: React.FC<TaskQuickViewProps> = ({
  task,
  onPress,
  onStatusChange,
  showActions = true,
  compact = false,
}) => {
  const getPriorityColor = () => {
    switch (task.priority) {
      case 'urgent':
        return '#D32F2F';
      case 'high':
        return '#F57C00';
      case 'medium':
        return '#1976D2';
      default:
        return '#388E3C';
    }
  };

  const getStatusColor = () => {
    switch (task.status) {
      case 'completed':
        return '#4CAF50';
      case 'in_progress':
        return '#FF9800';
      case 'review':
        return '#9C27B0';
      default:
        return '#757575';
    }
  };

  const getTypeIcon = () => {
    switch (task.type) {
      case 'bug':
        return 'bug';
      case 'feature':
        return 'star';
      case 'improvement':
        return 'trending-up';
      default:
        return 'check-circle-outline';
    }
  };

  const formatDueDate = () => {
    if (!task.dueDate) return null;
    
    const now = new Date();
    const due = new Date(task.dueDate);
    const diffDays = Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return 'Overdue';
    if (diffDays === 0) return 'Due today';
    if (diffDays === 1) return 'Due tomorrow';
    return `Due in ${diffDays} days`;
  };

  const getNextStatus = (): TaskData['status'] => {
    switch (task.status) {
      case 'pending':
        return 'in_progress';
      case 'in_progress':
        return 'review';
      case 'review':
        return 'completed';
      default:
        return 'pending';
    }
  };

  const handleStatusToggle = () => {
    if (onStatusChange) {
      onStatusChange(task.id, getNextStatus());
    }
  };

  const dueDateStatus = formatDueDate();
  const isOverdue = task.dueDate && new Date(task.dueDate) < new Date();

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <Card style={[styles.card, compact && styles.cardCompact]}>
        <Card.Content style={[styles.content, compact && styles.contentCompact]}>
          <View style={styles.header}>
            <View style={styles.typeIndicator}>
              <Avatar.Icon
                size={compact ? 32 : 40}
                icon={getTypeIcon()}
                style={[styles.typeIcon, { backgroundColor: getPriorityColor() }]}
              />
            </View>
            
            <View style={styles.titleContainer}>
              <Title style={[styles.title, compact && styles.titleCompact]}>
                {task.title}
              </Title>
              {!compact && task.description && (
                <Paragraph style={styles.description} numberOfLines={2}>
                  {task.description}
                </Paragraph>
              )}
            </View>

            {showActions && (
              <View style={styles.actions}>
                <IconButton
                  icon={task.status === 'completed' ? 'check-circle' : 'circle-outline'}
                  size={20}
                  iconColor={getStatusColor()}
                  onPress={handleStatusToggle}
                />
              </View>
            )}
          </View>

          <View style={styles.metadata}>
            <View style={styles.chips}>
              <Chip
                mode="outlined"
                compact
                style={[styles.statusChip, { borderColor: getStatusColor() }]}
                textStyle={{ color: getStatusColor(), fontSize: 10 }}
              >
                {task.status.replace('_', ' ').toUpperCase()}
              </Chip>
              
              <Chip
                mode="outlined"
                compact
                style={[styles.priorityChip, { borderColor: getPriorityColor() }]}
                textStyle={{ color: getPriorityColor(), fontSize: 10 }}
              >
                {task.priority.toUpperCase()}
              </Chip>
            </View>

            {dueDateStatus && (
              <View style={styles.dueDateContainer}>
                <Icon
                  name="calendar-clock"
                  size={12}
                  color={isOverdue ? '#D32F2F' : '#757575'}
                />
                <Paragraph
                  style={[
                    styles.dueDate,
                    { color: isOverdue ? '#D32F2F' : '#757575' }
                  ]}
                >
                  {dueDateStatus}
                </Paragraph>
              </View>
            )}
          </View>

          {!compact && (task.estimatedTime || task.actualTime) && (
            <View style={styles.timeInfo}>
              {task.estimatedTime && (
                <View style={styles.timeItem}>
                  <Icon name="clock-outline" size={12} color="#757575" />
                  <Paragraph style={styles.timeText}>
                    Est: {Math.round(task.estimatedTime / 60)}h
                  </Paragraph>
                </View>
              )}
              {task.actualTime && (
                <View style={styles.timeItem}>
                  <Icon name="clock" size={12} color="#757575" />
                  <Paragraph style={styles.timeText}>
                    Actual: {Math.round(task.actualTime / 60)}h
                  </Paragraph>
                </View>
              )}
            </View>
          )}

          {!compact && task.tags && task.tags.length > 0 && (
            <View style={styles.tags}>
              {task.tags.slice(0, 3).map((tag, index) => (
                <Chip
                  key={index}
                  mode="flat"
                  compact
                  style={styles.tag}
                  textStyle={styles.tagText}
                >
                  {tag}
                </Chip>
              ))}
              {task.tags.length > 3 && (
                <Paragraph style={styles.moreTagsText}>
                  +{task.tags.length - 3} more
                </Paragraph>
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
    borderRadius: 8,
  },
  cardCompact: {
    margin: 4,
  },
  content: {
    padding: 12,
  },
  contentCompact: {
    padding: 8,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  typeIndicator: {
    marginRight: 12,
  },
  typeIcon: {
    borderRadius: 8,
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
    marginBottom: 2,
  },
  description: {
    fontSize: 12,
    opacity: 0.7,
    lineHeight: 16,
  },
  actions: {
    marginLeft: 8,
  },
  metadata: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  chips: {
    flexDirection: 'row',
    flex: 1,
  },
  statusChip: {
    marginRight: 8,
    height: 24,
  },
  priorityChip: {
    height: 24,
  },
  dueDateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dueDate: {
    fontSize: 10,
    marginLeft: 4,
    fontWeight: '500',
  },
  timeInfo: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  timeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  timeText: {
    fontSize: 10,
    marginLeft: 4,
    opacity: 0.7,
  },
  tags: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  tag: {
    marginRight: 4,
    marginBottom: 4,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    height: 20,
  },
  tagText: {
    fontSize: 10,
  },
  moreTagsText: {
    fontSize: 10,
    opacity: 0.5,
    marginLeft: 4,
  },
});

export default TaskQuickView;
