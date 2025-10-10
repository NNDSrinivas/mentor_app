/**
 * Metric Card - Displays key metrics with visual indicators
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
  ProgressBar,
  IconButton,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface MetricData {
  id: string;
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  color: string;
  progress?: number;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  actionable?: boolean;
}

interface MetricCardProps {
  metric: MetricData;
  onPress?: () => void;
  size?: 'small' | 'medium' | 'large';
}

const MetricCard: React.FC<MetricCardProps> = ({
  metric,
  onPress,
  size = 'medium',
}) => {
  const getTrendIcon = () => {
    switch (metric.trend) {
      case 'up':
        return 'trending-up';
      case 'down':
        return 'trending-down';
      default:
        return 'trending-neutral';
    }
  };

  const getTrendColor = () => {
    switch (metric.trend) {
      case 'up':
        return '#4CAF50';
      case 'down':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };

  const cardStyle = [
    styles.card,
    size === 'small' && styles.cardSmall,
    size === 'large' && styles.cardLarge,
  ];

  const content = (
    <Card style={cardStyle}>
      <Card.Content style={styles.content}>
        <View style={styles.header}>
          <View style={[styles.iconContainer, { backgroundColor: metric.color }]}>
            <Icon 
              name={metric.icon} 
              size={size === 'small' ? 20 : 24} 
              color="#ffffff" 
            />
          </View>
          {metric.actionable && (
            <IconButton
              icon="chevron-right"
              size={16}
              onPress={onPress}
            />
          )}
        </View>

        <View style={styles.body}>
          <Title style={[
            styles.value, 
            size === 'small' && styles.valueSmall
          ]}>
            {metric.value}
          </Title>
          <Paragraph style={[
            styles.title,
            size === 'small' && styles.titleSmall
          ]}>
            {metric.title}
          </Paragraph>
          {metric.subtitle && (
            <Paragraph style={styles.subtitle}>
              {metric.subtitle}
            </Paragraph>
          )}
        </View>

        {metric.progress !== undefined && (
          <View style={styles.progressContainer}>
            <ProgressBar
              progress={metric.progress}
              color={metric.color}
              style={styles.progressBar}
            />
            <Paragraph style={styles.progressText}>
              {Math.round(metric.progress * 100)}%
            </Paragraph>
          </View>
        )}

        {metric.trend && metric.trendValue && (
          <View style={styles.trendContainer}>
            <Icon
              name={getTrendIcon()}
              size={16}
              color={getTrendColor()}
            />
            <Paragraph style={[
              styles.trendText,
              { color: getTrendColor() }
            ]}>
              {metric.trendValue}
            </Paragraph>
          </View>
        )}
      </Card.Content>
    </Card>
  );

  if (onPress) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
        {content}
      </TouchableOpacity>
    );
  }

  return content;
};

const styles = StyleSheet.create({
  card: {
    margin: 8,
    elevation: 4,
    borderRadius: 12,
  },
  cardSmall: {
    margin: 4,
  },
  cardLarge: {
    margin: 12,
  },
  content: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  body: {
    marginBottom: 12,
  },
  value: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  valueSmall: {
    fontSize: 20,
  },
  title: {
    fontSize: 14,
    opacity: 0.8,
    marginBottom: 2,
  },
  titleSmall: {
    fontSize: 12,
  },
  subtitle: {
    fontSize: 12,
    opacity: 0.6,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressBar: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    marginRight: 8,
  },
  progressText: {
    fontSize: 12,
    opacity: 0.8,
    minWidth: 35,
  },
  trendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  trendText: {
    fontSize: 12,
    marginLeft: 4,
    fontWeight: '500',
  },
});

export default MetricCard;
