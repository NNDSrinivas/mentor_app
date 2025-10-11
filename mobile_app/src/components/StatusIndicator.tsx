/**
 * Status Indicator - Shows system and connection status with visual indicators
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
} from 'react-native';
import {
  Surface,
  Paragraph,
  Chip,
  IconButton,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

export interface StatusData {
  connection: {
    status: 'connected' | 'connecting' | 'disconnected' | 'error';
    quality: 'excellent' | 'good' | 'fair' | 'poor';
    latency?: number;
    lastSync?: Date;
  };
  services: {
    ai: 'online' | 'offline' | 'degraded';
    sync: 'active' | 'paused' | 'error';
    notifications: 'enabled' | 'disabled';
    calendar: 'connected' | 'disconnected';
    offline: 'ready' | 'not_ready';
  };
  battery?: {
    level: number;
    isCharging: boolean;
    isLowPowerMode: boolean;
  };
  storage?: {
    used: number;
    available: number;
    total: number;
  };
}

interface StatusIndicatorProps {
  status: StatusData;
  onPress?: () => void;
  onRefresh?: () => void;
  compact?: boolean;
  showDetails?: boolean;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  onPress,
  onRefresh,
  compact = false,
  showDetails = true,
}) => {
  const [pulseAnim] = useState(new Animated.Value(1));
  const [rotateAnim] = useState(new Animated.Value(0));

  useEffect(() => {
    // Pulse animation for connecting state
    if (status.connection.status === 'connecting') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 0.6,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [status.connection.status, pulseAnim]);

  const getConnectionIcon = () => {
    switch (status.connection.status) {
      case 'connected':
        return 'wifi';
      case 'connecting':
        return 'wifi-sync';
      case 'disconnected':
        return 'wifi-off';
      case 'error':
        return 'wifi-alert';
      default:
        return 'wifi-strength-outline';
    }
  };

  const getConnectionColor = () => {
    switch (status.connection.status) {
      case 'connected':
        return getQualityColor();
      case 'connecting':
        return '#FF9800';
      case 'disconnected':
        return '#757575';
      case 'error':
        return '#F44336';
      default:
        return '#757575';
    }
  };

  const getQualityColor = () => {
    switch (status.connection.quality) {
      case 'excellent':
        return '#4CAF50';
      case 'good':
        return '#8BC34A';
      case 'fair':
        return '#FF9800';
      case 'poor':
        return '#F44336';
      default:
        return '#757575';
    }
  };

  const getServiceIcon = (service: keyof StatusData['services']) => {
    switch (service) {
      case 'ai':
        return 'brain';
      case 'sync':
        return 'sync';
      case 'notifications':
        return 'bell';
      case 'calendar':
        return 'calendar';
      case 'offline':
        return 'cloud-download';
      default:
        return 'cog';
    }
  };

  const getServiceColor = (service: keyof StatusData['services']) => {
    const serviceStatus = status.services[service];
    
    switch (serviceStatus) {
      case 'online':
      case 'active':
      case 'enabled':
      case 'connected':
      case 'ready':
        return '#4CAF50';
      case 'degraded':
      case 'paused':
        return '#FF9800';
      case 'offline':
      case 'error':
      case 'disabled':
      case 'disconnected':
      case 'not_ready':
        return '#F44336';
      default:
        return '#757575';
    }
  };

  const getBatteryIcon = () => {
    if (!status.battery) return 'battery-unknown';
    
    const { level, isCharging } = status.battery;
    
    if (isCharging) return 'battery-charging';
    if (level > 90) return 'battery';
    if (level > 60) return 'battery-70';
    if (level > 30) return 'battery-50';
    if (level > 10) return 'battery-30';
    return 'battery-10';
  };

  const getBatteryColor = () => {
    if (!status.battery) return '#757575';
    
    const { level, isCharging, isLowPowerMode } = status.battery;
    
    if (isCharging) return '#4CAF50';
    if (isLowPowerMode) return '#FF9800';
    if (level <= 20) return '#F44336';
    if (level <= 50) return '#FF9800';
    return '#4CAF50';
  };

  const formatLastSync = () => {
    if (!status.connection.lastSync) return 'Never';
    
    const now = new Date();
    const diff = now.getTime() - status.connection.lastSync.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const formatStorage = () => {
    if (!status.storage) return null;
    
    const { used, total } = status.storage;
    const usedGB = (used / (1024 * 1024 * 1024)).toFixed(1);
    const totalGB = (total / (1024 * 1024 * 1024)).toFixed(1);
    const percentage = Math.round((used / total) * 100);
    
    return `${usedGB}/${totalGB} GB (${percentage}%)`;
  };

  const handleRefresh = () => {
    if (onRefresh) {
      // Start rotation animation
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true,
      }).start(() => {
        rotateAnim.setValue(0);
      });
      
      onRefresh();
    }
  };

  const rotate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const content = (
    <Surface style={[styles.container, compact && styles.containerCompact]}>
      {/* Main Status */}
      <View style={styles.mainStatus}>
        <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
          <Icon
            name={getConnectionIcon()}
            size={compact ? 20 : 24}
            color={getConnectionColor()}
          />
        </Animated.View>
        
        {!compact && (
          <View style={styles.connectionInfo}>
            <Paragraph style={styles.connectionText}>
              {status.connection.status.charAt(0).toUpperCase() + status.connection.status.slice(1)}
            </Paragraph>
            {status.connection.latency && (
              <Paragraph style={styles.latencyText}>
                {status.connection.latency}ms
              </Paragraph>
            )}
          </View>
        )}

        <View style={styles.actions}>
          {onRefresh && (
            <Animated.View style={{ transform: [{ rotate }] }}>
              <IconButton
                icon="refresh"
                size={16}
                onPress={handleRefresh}
              />
            </Animated.View>
          )}
        </View>
      </View>

      {/* Service Status */}
      {showDetails && !compact && (
        <View style={styles.services}>
          {Object.entries(status.services).map(([service, serviceStatus]) => (
            <View key={service} style={styles.service}>
              <Icon
                name={getServiceIcon(service as keyof StatusData['services'])}
                size={12}
                color={getServiceColor(service as keyof StatusData['services'])}
              />
              <Paragraph style={styles.serviceText}>
                {service.charAt(0).toUpperCase() + service.slice(1)}
              </Paragraph>
            </View>
          ))}
        </View>
      )}

      {/* Additional Info */}
      {showDetails && !compact && (
        <View style={styles.additionalInfo}>
          {/* Battery */}
          {status.battery && (
            <View style={styles.infoItem}>
              <Icon
                name={getBatteryIcon()}
                size={12}
                color={getBatteryColor()}
              />
              <Paragraph style={styles.infoText}>
                {status.battery.level}%
                {status.battery.isLowPowerMode && ' (Low Power)'}
              </Paragraph>
            </View>
          )}

          {/* Storage */}
          {status.storage && (
            <View style={styles.infoItem}>
              <Icon name="harddisk" size={12} color="#757575" />
              <Paragraph style={styles.infoText}>
                {formatStorage()}
              </Paragraph>
            </View>
          )}

          {/* Last Sync */}
          <View style={styles.infoItem}>
            <Icon name="clock-outline" size={12} color="#757575" />
            <Paragraph style={styles.infoText}>
              {formatLastSync()}
            </Paragraph>
          </View>
        </View>
      )}

      {/* Compact Status Chips */}
      {compact && (
        <View style={styles.compactChips}>
          <Chip
            mode="flat"
            compact
            style={[styles.statusChip, { backgroundColor: getConnectionColor() + '20' }]}
            textStyle={{ color: getConnectionColor(), fontSize: 10 }}
          >
            {status.connection.status.toUpperCase()}
          </Chip>
          
          {status.battery && status.battery.level <= 20 && (
            <Chip
              mode="flat"
              compact
              style={[styles.batteryChip, { backgroundColor: getBatteryColor() + '20' }]}
              textStyle={{ color: getBatteryColor(), fontSize: 10 }}
            >
              {status.battery.level}%
            </Chip>
          )}
        </View>
      )}
    </Surface>
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
  container: {
    padding: 12,
    margin: 8,
    borderRadius: 8,
    elevation: 2,
  },
  containerCompact: {
    padding: 8,
    margin: 4,
  },
  mainStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  connectionInfo: {
    flex: 1,
    marginLeft: 8,
  },
  connectionText: {
    fontSize: 12,
    fontWeight: '600',
  },
  latencyText: {
    fontSize: 10,
    opacity: 0.7,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  services: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  service: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
    marginBottom: 4,
  },
  serviceText: {
    fontSize: 10,
    marginLeft: 4,
    opacity: 0.8,
  },
  additionalInfo: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    borderTopWidth: 1,
    borderTopColor: 'rgba(0, 0, 0, 0.1)',
    paddingTop: 8,
  },
  infoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
    marginBottom: 2,
  },
  infoText: {
    fontSize: 9,
    marginLeft: 4,
    opacity: 0.7,
  },
  compactChips: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusChip: {
    marginRight: 4,
    height: 20,
  },
  batteryChip: {
    height: 20,
  },
});

export default StatusIndicator;
