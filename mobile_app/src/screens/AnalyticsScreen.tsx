/**
 * Analytics Screen - Productivity metrics and insights dashboard
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
} from 'react-native';
import {
  Appbar,
  Searchbar,
  Chip,
  Button,
  Title,
  Paragraph,
  Surface,
  Card,
  Portal,
  Modal,
  SegmentedButtons,
  List,
  Divider,
} from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { LineChart, BarChart, PieChart } from 'react-native-chart-kit';

import { MetricCard, StatusIndicator } from '../components';
import type { MetricData } from '../components/MetricCard';
import type { RootState } from '../store';

const { width: screenWidth } = Dimensions.get('window');

interface ProductivityData {
  daily: {
    date: string;
    commits: number;
    linesWritten: number;
    meetingsAttended: number;
    tasksCompleted: number;
    focusTime: number; // minutes
  }[];
  weekly: {
    week: string;
    productivity: number;
    codeQuality: number;
    collaboration: number;
    learning: number;
  }[];
  monthly: {
    month: string;
    totalCommits: number;
    avgProductivity: number;
    projectsCompleted: number;
    skillsImproved: number;
  }[];
}

interface TeamMetrics {
  teamSize: number;
  activeContributors: number;
  avgResponseTime: number; // hours
  collaborationScore: number;
  knowledgeSharing: number;
  codeReviewEfficiency: number;
}

interface PersonalInsights {
  productivityTrend: 'increasing' | 'decreasing' | 'stable';
  bestPerformanceTime: string;
  focusPatterns: string[];
  improvementAreas: string[];
  achievements: {
    title: string;
    description: string;
    date: Date;
    type: 'milestone' | 'improvement' | 'collaboration';
  }[];
  recommendations: {
    title: string;
    description: string;
    priority: 'high' | 'medium' | 'low';
    category: 'productivity' | 'learning' | 'health' | 'collaboration';
  }[];
}

const AnalyticsScreen: React.FC = () => {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState('overview');
  const [timeRange, setTimeRange] = useState('week');
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [productivityData, setProductivityData] = useState<ProductivityData | null>(null);
  const [teamMetrics, setTeamMetrics] = useState<TeamMetrics | null>(null);
  const [personalInsights, setPersonalInsights] = useState<PersonalInsights | null>(null);
  const [showInsightsModal, setShowInsightsModal] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      loadAnalyticsData();
    }, [timeRange])
  );

  const loadAnalyticsData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadProductivityData(),
        loadTeamMetrics(),
        loadPersonalInsights(),
      ]);
    } catch (error) {
      console.error('Error loading analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadProductivityData = async () => {
    // Mock productivity data
    const mockData: ProductivityData = {
      daily: [
        { date: '2025-10-01', commits: 8, linesWritten: 650, meetingsAttended: 3, tasksCompleted: 5, focusTime: 420 },
        { date: '2025-10-02', commits: 12, linesWritten: 890, meetingsAttended: 2, tasksCompleted: 7, focusTime: 480 },
        { date: '2025-10-03', commits: 6, linesWritten: 420, meetingsAttended: 4, tasksCompleted: 4, focusTime: 360 },
        { date: '2025-10-04', commits: 15, linesWritten: 1200, meetingsAttended: 1, tasksCompleted: 8, focusTime: 540 },
        { date: '2025-10-05', commits: 10, linesWritten: 750, meetingsAttended: 3, tasksCompleted: 6, focusTime: 450 },
        { date: '2025-10-06', commits: 4, linesWritten: 280, meetingsAttended: 5, tasksCompleted: 3, focusTime: 240 },
        { date: '2025-10-07', commits: 9, linesWritten: 680, meetingsAttended: 2, tasksCompleted: 5, focusTime: 390 },
      ],
      weekly: [
        { week: 'Week 1', productivity: 85, codeQuality: 78, collaboration: 92, learning: 65 },
        { week: 'Week 2', productivity: 92, codeQuality: 85, collaboration: 88, learning: 72 },
        { week: 'Week 3', productivity: 78, codeQuality: 90, collaboration: 95, learning: 80 },
        { week: 'Week 4', productivity: 88, codeQuality: 82, collaboration: 85, learning: 75 },
      ],
      monthly: [
        { month: 'Aug', totalCommits: 180, avgProductivity: 82, projectsCompleted: 3, skillsImproved: 5 },
        { month: 'Sep', totalCommits: 205, avgProductivity: 88, projectsCompleted: 4, skillsImproved: 7 },
        { month: 'Oct', totalCommits: 165, avgProductivity: 85, projectsCompleted: 2, skillsImproved: 6 },
      ],
    };
    setProductivityData(mockData);
  };

  const loadTeamMetrics = async () => {
    const mockTeamMetrics: TeamMetrics = {
      teamSize: 12,
      activeContributors: 8,
      avgResponseTime: 2.5,
      collaborationScore: 88,
      knowledgeSharing: 75,
      codeReviewEfficiency: 92,
    };
    setTeamMetrics(mockTeamMetrics);
  };

  const loadPersonalInsights = async () => {
    const mockInsights: PersonalInsights = {
      productivityTrend: 'increasing',
      bestPerformanceTime: '9:00 AM - 11:00 AM',
      focusPatterns: [
        'Most productive on Tuesdays and Thursdays',
        'Deep work sessions average 90 minutes',
        'Fewer meetings in morning = higher code output',
      ],
      improvementAreas: [
        'Code review response time',
        'Documentation consistency',
        'Test coverage improvement',
      ],
      achievements: [
        {
          title: 'Sprint Goal Champion',
          description: 'Completed 100% of sprint commitments for 3 consecutive sprints',
          date: new Date(2025, 9, 5),
          type: 'milestone',
        },
        {
          title: 'Code Quality Improver',
          description: 'Reduced code complexity by 25% in last month',
          date: new Date(2025, 9, 2),
          type: 'improvement',
        },
        {
          title: 'Team Collaborator',
          description: 'Provided helpful reviews on 15+ pull requests',
          date: new Date(2025, 8, 28),
          type: 'collaboration',
        },
      ],
      recommendations: [
        {
          title: 'Schedule Focus Blocks',
          description: 'Block 2-hour morning sessions for deep work to maximize your peak performance time',
          priority: 'high',
          category: 'productivity',
        },
        {
          title: 'Learn Advanced React Patterns',
          description: 'Based on your recent code, exploring React patterns could enhance your development efficiency',
          priority: 'medium',
          category: 'learning',
        },
        {
          title: 'Take Regular Breaks',
          description: 'Your focus sessions are getting longer. Consider 15-minute breaks every 90 minutes',
          priority: 'medium',
          category: 'health',
        },
      ],
    };
    setPersonalInsights(mockInsights);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadAnalyticsData();
    setRefreshing(false);
  };

  const getOverviewMetrics = (): MetricData[] => {
    if (!productivityData || !teamMetrics) return [];

    const weekData = productivityData.daily.slice(-7);
    const totalCommits = weekData.reduce((sum, day) => sum + day.commits, 0);
    const totalFocusTime = weekData.reduce((sum, day) => sum + day.focusTime, 0);
    const avgProductivity = totalFocusTime / (7 * 480); // 8 hours per day

    return [
      {
        id: 'productivity',
        title: 'Productivity Score',
        value: Math.round(avgProductivity * 100),
        subtitle: 'This week',
        icon: 'speedometer',
        color: '#4CAF50',
        progress: avgProductivity,
        trend: 'up',
        trendValue: '+8%',
        actionable: true,
      },
      {
        id: 'commits',
        title: 'Weekly Commits',
        value: totalCommits,
        subtitle: 'Code contributions',
        icon: 'source-commit',
        color: '#2196F3',
        trend: 'up',
        trendValue: '+12',
        actionable: false,
      },
      {
        id: 'focus',
        title: 'Focus Time',
        value: `${Math.round(totalFocusTime / 60)}h`,
        subtitle: 'Deep work sessions',
        icon: 'brain',
        color: '#9C27B0',
        progress: totalFocusTime / (7 * 480),
        actionable: true,
      },
      {
        id: 'collaboration',
        title: 'Team Score',
        value: `${teamMetrics.collaborationScore}%`,
        subtitle: 'Collaboration rating',
        icon: 'account-group',
        color: '#FF9800',
        progress: teamMetrics.collaborationScore / 100,
        trend: 'stable',
        trendValue: '0%',
        actionable: true,
      },
    ];
  };

  const getChartData = () => {
    if (!productivityData) return null;

    const daily = productivityData.daily.slice(-7);
    
    return {
      labels: daily.map(d => new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' })),
      datasets: [
        {
          data: daily.map(d => d.commits),
          color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
          strokeWidth: 2,
        },
      ],
    };
  };

  const getProductivityChart = () => {
    if (!productivityData) return null;

    const weekly = productivityData.weekly;
    
    return {
      labels: weekly.map(w => w.week),
      datasets: [
        {
          data: weekly.map(w => w.productivity),
          color: (opacity = 1) => `rgba(76, 175, 80, ${opacity})`,
        },
        {
          data: weekly.map(w => w.codeQuality),
          color: (opacity = 1) => `rgba(156, 39, 176, ${opacity})`,
        },
        {
          data: weekly.map(w => w.collaboration),
          color: (opacity = 1) => `rgba(255, 152, 0, ${opacity})`,
        },
      ],
    };
  };

  const getAchievementIcon = (type: string) => {
    switch (type) {
      case 'milestone':
        return 'trophy';
      case 'improvement':
        return 'trending-up';
      case 'collaboration':
        return 'account-group';
      default:
        return 'star';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return '#F44336';
      case 'medium':
        return '#FF9800';
      default:
        return '#4CAF50';
    }
  };

  const renderOverview = () => {
    const metrics = getOverviewMetrics();
    const chartData = getChartData();

    return (
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Metrics Cards */}
        <View style={styles.metricsGrid}>
          {metrics.map((metric) => (
            <MetricCard
              key={metric.id}
              metric={metric}
              onPress={() => setShowInsightsModal(true)}
              size="medium"
            />
          ))}
        </View>

        {/* Commits Chart */}
        {chartData && (
          <Card style={styles.chartCard}>
            <Card.Content>
              <Title style={styles.chartTitle}>Daily Commits</Title>
              <LineChart
                data={chartData}
                width={screenWidth - 64}
                height={200}
                chartConfig={{
                  backgroundColor: '#ffffff',
                  backgroundGradientFrom: '#ffffff',
                  backgroundGradientTo: '#ffffff',
                  decimalPlaces: 0,
                  color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
                  style: { borderRadius: 16 },
                }}
                bezier
                style={styles.chart}
              />
            </Card.Content>
          </Card>
        )}

        {/* Quick Insights */}
        <Card style={styles.insightsCard}>
          <Card.Content>
            <Title style={styles.insightsTitle}>Quick Insights</Title>
            {personalInsights?.focusPatterns.slice(0, 2).map((pattern, index) => (
              <View key={index} style={styles.insightItem}>
                <Icon name="lightbulb" size={16} color="#FF9800" />
                <Paragraph style={styles.insightText}>{pattern}</Paragraph>
              </View>
            ))}
          </Card.Content>
        </Card>
      </ScrollView>
    );
  };

  const renderTrends = () => {
    const productivityChart = getProductivityChart();

    return (
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Productivity Trends */}
        {productivityChart && (
          <Card style={styles.chartCard}>
            <Card.Content>
              <Title style={styles.chartTitle}>Weekly Productivity Trends</Title>
              <LineChart
                data={productivityChart}
                width={screenWidth - 64}
                height={220}
                chartConfig={{
                  backgroundColor: '#ffffff',
                  backgroundGradientFrom: '#ffffff',
                  backgroundGradientTo: '#ffffff',
                  decimalPlaces: 0,
                  color: (opacity = 1) => `rgba(76, 175, 80, ${opacity})`,
                  style: { borderRadius: 16 },
                }}
                style={styles.chart}
              />
              <View style={styles.chartLegend}>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#4CAF50' }]} />
                  <Paragraph style={styles.legendText}>Productivity</Paragraph>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#9C27B0' }]} />
                  <Paragraph style={styles.legendText}>Code Quality</Paragraph>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#FF9800' }]} />
                  <Paragraph style={styles.legendText}>Collaboration</Paragraph>
                </View>
              </View>
            </Card.Content>
          </Card>
        )}

        {/* Team Metrics */}
        {teamMetrics && (
          <Card style={styles.teamCard}>
            <Card.Content>
              <Title style={styles.teamTitle}>Team Performance</Title>
              <View style={styles.teamMetrics}>
                <View style={styles.teamMetric}>
                  <Paragraph style={styles.teamMetricValue}>{teamMetrics.teamSize}</Paragraph>
                  <Paragraph style={styles.teamMetricLabel}>Team Size</Paragraph>
                </View>
                <View style={styles.teamMetric}>
                  <Paragraph style={styles.teamMetricValue}>{teamMetrics.collaborationScore}%</Paragraph>
                  <Paragraph style={styles.teamMetricLabel}>Collaboration</Paragraph>
                </View>
                <View style={styles.teamMetric}>
                  <Paragraph style={styles.teamMetricValue}>{teamMetrics.avgResponseTime}h</Paragraph>
                  <Paragraph style={styles.teamMetricLabel}>Response Time</Paragraph>
                </View>
              </View>
            </Card.Content>
          </Card>
        )}
      </ScrollView>
    );
  };

  const renderInsights = () => (
    <ScrollView showsVerticalScrollIndicator={false}>
      {/* Achievements */}
      <Card style={styles.achievementsCard}>
        <Card.Content>
          <Title style={styles.achievementsTitle}>Recent Achievements</Title>
          {personalInsights?.achievements.map((achievement, index) => (
            <List.Item
              key={index}
              title={achievement.title}
              description={achievement.description}
              left={(props) => (
                <Icon
                  {...props}
                  name={getAchievementIcon(achievement.type)}
                  size={24}
                  color="#FFD700"
                />
              )}
              style={styles.achievementItem}
            />
          ))}
        </Card.Content>
      </Card>

      {/* Recommendations */}
      <Card style={styles.recommendationsCard}>
        <Card.Content>
          <Title style={styles.recommendationsTitle}>AI Recommendations</Title>
          {personalInsights?.recommendations.map((rec, index) => (
            <View key={index} style={styles.recommendationItem}>
              <View style={styles.recommendationHeader}>
                <Title style={styles.recommendationTitle}>{rec.title}</Title>
                <Chip
                  mode="outlined"
                  compact
                  style={[styles.priorityChip, { borderColor: getPriorityColor(rec.priority) }]}
                  textStyle={{ color: getPriorityColor(rec.priority) }}
                >
                  {rec.priority.toUpperCase()}
                </Chip>
              </View>
              <Paragraph style={styles.recommendationDescription}>
                {rec.description}
              </Paragraph>
              <Chip mode="flat" compact style={styles.categoryChip}>
                {rec.category.toUpperCase()}
              </Chip>
            </View>
          ))}
        </Card.Content>
      </Card>
    </ScrollView>
  );

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.Content title="Analytics" />
        <Appbar.Action icon="download" onPress={() => {}} />
        <Appbar.Action icon="refresh" onPress={handleRefresh} />
      </Appbar.Header>

      <View style={styles.content}>
        {/* Time Range Filter */}
        <SegmentedButtons
          value={timeRange}
          onValueChange={setTimeRange}
          buttons={[
            { value: 'week', label: 'Week' },
            { value: 'month', label: 'Month' },
            { value: 'quarter', label: 'Quarter' },
          ]}
          style={styles.timeRange}
        />

        {/* Tab Navigation */}
        <SegmentedButtons
          value={activeTab}
          onValueChange={setActiveTab}
          buttons={[
            { value: 'overview', label: 'Overview', icon: 'view-dashboard' },
            { value: 'trends', label: 'Trends', icon: 'trending-up' },
            { value: 'insights', label: 'Insights', icon: 'lightbulb' },
          ]}
          style={styles.tabs}
        />

        {/* Content */}
        <ScrollView
          style={styles.contentScroll}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'trends' && renderTrends()}
          {activeTab === 'insights' && renderInsights()}
        </ScrollView>
      </View>

      {/* Insights Modal */}
      <Portal>
        <Modal
          visible={showInsightsModal}
          onDismiss={() => setShowInsightsModal(false)}
          contentContainerStyle={styles.modalContent}
        >
          <Title>Detailed Insights</Title>
          {personalInsights && (
            <ScrollView style={styles.modalScroll}>
              <View style={styles.insightSection}>
                <Paragraph style={styles.sectionTitle}>Best Performance Time</Paragraph>
                <Paragraph style={styles.sectionValue}>{personalInsights.bestPerformanceTime}</Paragraph>
              </View>

              <View style={styles.insightSection}>
                <Paragraph style={styles.sectionTitle}>Productivity Trend</Paragraph>
                <Paragraph style={[
                  styles.sectionValue,
                  { color: personalInsights.productivityTrend === 'increasing' ? '#4CAF50' : '#FF9800' }
                ]}>
                  {personalInsights.productivityTrend.toUpperCase()}
                </Paragraph>
              </View>

              <View style={styles.insightSection}>
                <Paragraph style={styles.sectionTitle}>Areas for Improvement</Paragraph>
                {personalInsights.improvementAreas.map((area, index) => (
                  <Paragraph key={index} style={styles.improvementArea}>
                    • {area}
                  </Paragraph>
                ))}
              </View>
            </ScrollView>
          )}
          <Button mode="contained" onPress={() => setShowInsightsModal(false)}>
            Close
          </Button>
        </Modal>
      </Portal>

      {/* Status Indicator */}
      <StatusIndicator
        status={{
          connection: {
            status: 'connected',
            quality: 'excellent',
            latency: 28,
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
  timeRange: {
    marginBottom: 8,
  },
  tabs: {
    marginBottom: 16,
  },
  contentScroll: {
    flex: 1,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  chartCard: {
    marginBottom: 16,
    elevation: 2,
  },
  chartTitle: {
    fontSize: 16,
    marginBottom: 8,
  },
  chart: {
    borderRadius: 8,
  },
  chartLegend: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 8,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 8,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
  legendText: {
    fontSize: 10,
  },
  insightsCard: {
    marginBottom: 16,
    elevation: 2,
  },
  insightsTitle: {
    fontSize: 16,
    marginBottom: 8,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  insightText: {
    fontSize: 12,
    marginLeft: 8,
    flex: 1,
    lineHeight: 16,
  },
  teamCard: {
    marginBottom: 16,
    elevation: 2,
  },
  teamTitle: {
    fontSize: 16,
    marginBottom: 8,
  },
  teamMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  teamMetric: {
    alignItems: 'center',
  },
  teamMetricValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  teamMetricLabel: {
    fontSize: 10,
    opacity: 0.7,
  },
  achievementsCard: {
    marginBottom: 16,
    elevation: 2,
  },
  achievementsTitle: {
    fontSize: 16,
    marginBottom: 8,
  },
  achievementItem: {
    paddingVertical: 4,
  },
  recommendationsCard: {
    marginBottom: 16,
    elevation: 2,
  },
  recommendationsTitle: {
    fontSize: 16,
    marginBottom: 8,
  },
  recommendationItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 0, 0, 0.1)',
  },
  recommendationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  recommendationTitle: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  priorityChip: {
    height: 20,
  },
  recommendationDescription: {
    fontSize: 12,
    lineHeight: 16,
    marginBottom: 8,
  },
  categoryChip: {
    alignSelf: 'flex-start',
    height: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
  },
  modalContent: {
    backgroundColor: 'white',
    padding: 20,
    margin: 20,
    borderRadius: 8,
    maxHeight: '80%',
  },
  modalScroll: {
    marginVertical: 16,
  },
  insightSection: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 0, 0, 0.1)',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
  },
  sectionValue: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  improvementArea: {
    fontSize: 12,
    marginBottom: 4,
    marginLeft: 8,
  },
});

export default AnalyticsScreen;
