/**
 * AI Insight Card - Displays AI-generated insights and recommendations
 */

import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Button,
  Chip,
  IconButton,
  ProgressBar,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface AIInsightData {
  id: string;
  title: string;
  description: string;
  type: 'recommendation' | 'prediction' | 'analysis' | 'warning' | 'tip';
  priority: 'low' | 'medium' | 'high' | 'critical';
  confidence: number; // 0-1
  category: 'productivity' | 'code_quality' | 'meeting' | 'learning' | 'security';
  actionable: boolean;
  actions?: Array<{
    id: string;
    label: string;
    type: 'primary' | 'secondary';
  }>;
  metrics?: {
    impact: number; // 0-1
    effort: number; // 0-1
    timeToImplement?: string;
  };
  tags?: string[];
  timestamp: Date;
  isNew?: boolean;
  isDismissed?: boolean;
}

interface AIInsightCardProps {
  insight: AIInsightData;
  onAction?: (actionId: string) => void;
  onDismiss?: () => void;
  onExpand?: () => void;
  compact?: boolean;
  showMetrics?: boolean;
}

const AIInsightCard: React.FC<AIInsightCardProps> = ({
  insight,
  onAction,
  onDismiss,
  onExpand,
  compact = false,
  showMetrics = true,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [animation] = useState(new Animated.Value(0));

  const getTypeIcon = () => {
    switch (insight.type) {
      case 'recommendation':
        return 'lightbulb';
      case 'prediction':
        return 'crystal-ball';
      case 'analysis':
        return 'chart-line';
      case 'warning':
        return 'alert';
      default:
        return 'information';
    }
  };

  const getTypeColor = () => {
    switch (insight.type) {
      case 'recommendation':
        return '#2196F3';
      case 'prediction':
        return '#9C27B0';
      case 'analysis':
        return '#4CAF50';
      case 'warning':
        return '#FF9800';
      default:
        return '#607D8B';
    }
  };

  const getPriorityColor = () => {
    switch (insight.priority) {
      case 'critical':
        return '#D32F2F';
      case 'high':
        return '#F57C00';
      case 'medium':
        return '#1976D2';
      default:
        return '#388E3C';
    }
  };

  const getCategoryIcon = () => {
    switch (insight.category) {
      case 'productivity':
        return 'speedometer';
      case 'code_quality':
        return 'code-tags';
      case 'meeting':
        return 'calendar-account';
      case 'learning':
        return 'school';
      case 'security':
        return 'shield-check';
      default:
        return 'information';
    }
  };

  const toggleExpanded = () => {
    const toValue = expanded ? 0 : 1;
    setExpanded(!expanded);
    
    Animated.timing(animation, {
      toValue,
      duration: 300,
      useNativeDriver: false,
    }).start();

    if (onExpand) {
      onExpand();
    }
  };

  const formatTimestamp = () => {
    const now = new Date();
    const diffHours = Math.round((now.getTime() - insight.timestamp.getTime()) / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.round(diffHours / 24)}d ago`;
  };

  const animatedHeight = animation.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 200],
  });

  return (
    <Card style={[
      styles.card,
      compact && styles.cardCompact,
      insight.isNew && styles.cardNew,
      { borderLeftColor: getTypeColor() }
    ]}>
      <Card.Content style={[styles.content, compact && styles.contentCompact]}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Icon
              name={getTypeIcon()}
              size={20}
              color={getTypeColor()}
              style={styles.typeIcon}
            />
            <Icon
              name={getCategoryIcon()}
              size={12}
              color="#757575"
              style={styles.categoryIcon}
            />
          </View>

          <View style={styles.titleContainer}>
            <View style={styles.titleRow}>
              <Title style={[styles.title, compact && styles.titleCompact]}>
                {insight.title}
              </Title>
              {insight.isNew && (
                <Chip
                  mode="flat"
                  compact
                  style={styles.newChip}
                  textStyle={styles.newChipText}
                >
                  NEW
                </Chip>
              )}
            </View>
            
            <View style={styles.metaRow}>
              <Chip
                mode="outlined"
                compact
                style={[styles.priorityChip, { borderColor: getPriorityColor() }]}
                textStyle={{ color: getPriorityColor(), fontSize: 10 }}
              >
                {insight.priority.toUpperCase()}
              </Chip>
              <Paragraph style={styles.timestamp}>
                {formatTimestamp()}
              </Paragraph>
            </View>
          </View>

          <View style={styles.actions}>
            {!compact && (
              <IconButton
                icon={expanded ? 'chevron-up' : 'chevron-down'}
                size={20}
                onPress={toggleExpanded}
              />
            )}
            {onDismiss && (
              <IconButton
                icon="close"
                size={16}
                onPress={onDismiss}
              />
            )}
          </View>
        </View>

        {/* Description */}
        <Paragraph style={[
          styles.description,
          compact && styles.descriptionCompact
        ]} numberOfLines={compact ? 2 : 3}>
          {insight.description}
        </Paragraph>

        {/* Confidence Indicator */}
        <View style={styles.confidenceContainer}>
          <Icon name="brain" size={12} color="#9C27B0" />
          <Paragraph style={styles.confidenceLabel}>Confidence</Paragraph>
          <ProgressBar
            progress={insight.confidence}
            color="#9C27B0"
            style={styles.confidenceBar}
          />
          <Paragraph style={styles.confidenceText}>
            {Math.round(insight.confidence * 100)}%
          </Paragraph>
        </View>

        {/* Expanded Content */}
        {!compact && (
          <Animated.View style={[styles.expandedContent, { height: animatedHeight }]}>
            {expanded && (
              <View style={styles.expandedInner}>
                {/* Metrics */}
                {showMetrics && insight.metrics && (
                  <View style={styles.metricsContainer}>
                    <Title style={styles.metricsTitle}>Impact Analysis</Title>
                    <View style={styles.metricsRow}>
                      <View style={styles.metric}>
                        <Paragraph style={styles.metricLabel}>Impact</Paragraph>
                        <ProgressBar
                          progress={insight.metrics.impact}
                          color="#4CAF50"
                          style={styles.metricBar}
                        />
                        <Paragraph style={styles.metricValue}>
                          {Math.round(insight.metrics.impact * 100)}%
                        </Paragraph>
                      </View>
                      <View style={styles.metric}>
                        <Paragraph style={styles.metricLabel}>Effort</Paragraph>
                        <ProgressBar
                          progress={insight.metrics.effort}
                          color="#FF9800"
                          style={styles.metricBar}
                        />
                        <Paragraph style={styles.metricValue}>
                          {Math.round(insight.metrics.effort * 100)}%
                        </Paragraph>
                      </View>
                    </View>
                    {insight.metrics.timeToImplement && (
                      <Paragraph style={styles.timeToImplement}>
                        Time to implement: {insight.metrics.timeToImplement}
                      </Paragraph>
                    )}
                  </View>
                )}

                {/* Tags */}
                {insight.tags && insight.tags.length > 0 && (
                  <View style={styles.tagsContainer}>
                    {insight.tags.map((tag, index) => (
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
                  </View>
                )}
              </View>
            )}
          </Animated.View>
        )}

        {/* Action Buttons */}
        {insight.actionable && insight.actions && insight.actions.length > 0 && (
          <View style={styles.actionButtons}>
            {insight.actions.map((action) => (
              <Button
                key={action.id}
                mode={action.type === 'primary' ? 'contained' : 'outlined'}
                compact
                onPress={() => onAction?.(action.id)}
                style={[
                  styles.actionButton,
                  action.type === 'primary' && { backgroundColor: getTypeColor() }
                ]}
                labelStyle={styles.actionButtonText}
              >
                {action.label}
              </Button>
            ))}
          </View>
        )}
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: {
    margin: 8,
    elevation: 3,
    borderRadius: 12,
    borderLeftWidth: 4,
  },
  cardCompact: {
    margin: 4,
  },
  cardNew: {
    elevation: 6,
    shadowColor: '#2196F3',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
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
    marginBottom: 8,
  },
  iconContainer: {
    position: 'relative',
    marginRight: 12,
    width: 24,
    height: 24,
  },
  typeIcon: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  categoryIcon: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    backgroundColor: '#ffffff',
    borderRadius: 6,
    padding: 1,
  },
  titleContainer: {
    flex: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  titleCompact: {
    fontSize: 14,
  },
  newChip: {
    backgroundColor: '#2196F3',
    height: 20,
    marginLeft: 8,
  },
  newChipText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  priorityChip: {
    height: 20,
    marginRight: 8,
  },
  timestamp: {
    fontSize: 10,
    opacity: 0.6,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  description: {
    fontSize: 12,
    lineHeight: 16,
    marginBottom: 8,
    opacity: 0.8,
  },
  descriptionCompact: {
    fontSize: 11,
  },
  confidenceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  confidenceLabel: {
    fontSize: 10,
    marginLeft: 4,
    marginRight: 8,
    opacity: 0.7,
  },
  confidenceBar: {
    flex: 1,
    height: 3,
    borderRadius: 1.5,
    marginRight: 8,
  },
  confidenceText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#9C27B0',
    minWidth: 30,
  },
  expandedContent: {
    overflow: 'hidden',
  },
  expandedInner: {
    padding: 8,
  },
  metricsContainer: {
    marginBottom: 12,
  },
  metricsTitle: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metric: {
    flex: 1,
    marginHorizontal: 4,
  },
  metricLabel: {
    fontSize: 10,
    opacity: 0.7,
    marginBottom: 4,
  },
  metricBar: {
    height: 4,
    borderRadius: 2,
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 10,
    fontWeight: '600',
    textAlign: 'center',
  },
  timeToImplement: {
    fontSize: 10,
    fontStyle: 'italic',
    opacity: 0.7,
    marginTop: 4,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  tag: {
    marginRight: 4,
    marginBottom: 4,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    height: 20,
  },
  tagText: {
    fontSize: 9,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
  },
  actionButton: {
    marginLeft: 8,
  },
  actionButtonText: {
    fontSize: 11,
  },
});

export default AIInsightCard;
