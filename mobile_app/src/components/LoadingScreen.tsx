/**
 * Loading Screen - Elegant loading screen with animations
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import {
  ActivityIndicator,
  Title,
  Paragraph,
  Surface,
} from 'react-native-paper';
import LinearGradient from 'react-native-linear-gradient';

const { width, height } = Dimensions.get('window');

interface LoadingScreenProps {
  message?: string;
  progress?: number;
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({ 
  message = 'Loading AI SDLC Assistant...', 
  progress 
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Start animations
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        tension: 100,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous rotation for the logo
    Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 2000,
        useNativeDriver: true,
      })
    ).start();
  }, [fadeAnim, scaleAnim, rotateAnim]);

  const rotate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <Animated.View
        style={[
          styles.content,
          {
            opacity: fadeAnim,
            transform: [{ scale: scaleAnim }],
          },
        ]}
      >
        <Surface style={styles.logoContainer}>
          <Animated.View style={{ transform: [{ rotate }] }}>
            <View style={styles.logo}>
              <Title style={styles.logoText}>AI</Title>
            </View>
          </Animated.View>
        </Surface>

        <View style={styles.textContainer}>
          <Title style={styles.title}>AI SDLC Assistant</Title>
          <Paragraph style={styles.subtitle}>
            Intelligent Software Development Lifecycle
          </Paragraph>
          <Paragraph style={styles.message}>{message}</Paragraph>
        </View>

        <View style={styles.loadingContainer}>
          <ActivityIndicator
            size="large"
            color="#ffffff"
            style={styles.spinner}
          />
          {progress !== undefined && (
            <Paragraph style={styles.progressText}>
              {Math.round(progress * 100)}%
            </Paragraph>
          )}
        </View>
      </Animated.View>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    alignItems: 'center',
    justifyContent: 'center',
    width: width * 0.8,
  },
  logoContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginBottom: 40,
  },
  logo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    color: '#ffffff',
    fontSize: 28,
    fontWeight: 'bold',
  },
  textContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    color: '#ffffff',
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  message: {
    color: 'rgba(255, 255, 255, 0.9)',
    fontSize: 14,
    textAlign: 'center',
  },
  loadingContainer: {
    alignItems: 'center',
  },
  spinner: {
    marginBottom: 10,
  },
  progressText: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 12,
  },
});

export default LoadingScreen;
