/**
 * Code Screen - Code review and repository management interface
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
  Card,
  Portal,
  Modal,
  SegmentedButtons,
  Badge,
  List,
  Avatar,
} from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import { MetricCard, StatusIndicator } from '../components';
import type { MetricData } from '../components/MetricCard';
import type { RootState } from '../store';

interface Repository {
  id: string;
  name: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  openIssues: number;
  lastCommit: Date;
  branch: string;
  status: 'active' | 'archived' | 'private';
}

interface PullRequest {
  id: string;
  title: string;
  description: string;
  author: string;
  reviewers: string[];
  status: 'open' | 'merged' | 'closed' | 'draft';
  createdAt: Date;
  updatedAt: Date;
  additions: number;
  deletions: number;
  commits: number;
  repository: string;
  branch: string;
  targetBranch: string;
  conflicts: boolean;
  checks: {
    passed: number;
    failed: number;
    pending: number;
  };
}

interface CodeMetrics {
  codeQuality: {
    score: number;
    bugs: number;
    vulnerabilities: number;
    codeSmells: number;
    coverage: number;
  };
  productivity: {
    commitsToday: number;
    linesWritten: number;
    filesModified: number;
    pullRequestsCreated: number;
    pullRequestsReviewed: number;
  };
  team: {
    activeContributors: number;
    reviewTime: number; // hours
    mergeRate: number; // percentage
  };
}

const CodeScreen: React.FC = () => {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState('repositories');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [codeMetrics, setCodeMetrics] = useState<CodeMetrics | null>(null);
  const [showMetricsModal, setShowMetricsModal] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      loadData();
    }, [])
  );

  const loadData = async () => {
    setLoading(true);
    try {
      // Simulate API calls
      await Promise.all([
        loadRepositories(),
        loadPullRequests(),
        loadCodeMetrics(),
      ]);
    } catch (error) {
      console.error('Error loading code data:', error);
      Alert.alert('Error', 'Failed to load code data');
    } finally {
      setLoading(false);
    }
  };

  const loadRepositories = async () => {
    const mockRepos: Repository[] = [
      {
        id: '1',
        name: 'mentor-app',
        description: 'AI-powered SDLC assistant with meeting intelligence',
        language: 'TypeScript',
        stars: 42,
        forks: 8,
        openIssues: 12,
        lastCommit: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        branch: 'main',
        status: 'active',
      },
      {
        id: '2',
        name: 'mobile-app',
        description: 'React Native mobile application',
        language: 'TypeScript',
        stars: 15,
        forks: 3,
        openIssues: 5,
        lastCommit: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
        branch: 'development',
        status: 'active',
      },
      {
        id: '3',
        name: 'analytics-dashboard',
        description: 'Data visualization and analytics platform',
        language: 'Python',
        stars: 28,
        forks: 6,
        openIssues: 8,
        lastCommit: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
        branch: 'main',
        status: 'active',
      },
    ];
    setRepositories(mockRepos);
  };

  const loadPullRequests = async () => {
    const mockPRs: PullRequest[] = [
      {
        id: '1',
        title: 'Add mobile app component library',
        description: 'Implement reusable components for mobile app UI',
        author: 'john.doe',
        reviewers: ['jane.smith', 'alice.johnson'],
        status: 'open',
        createdAt: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
        updatedAt: new Date(Date.now() - 1 * 60 * 60 * 1000), // 1 hour ago
        additions: 1250,
        deletions: 45,
        commits: 8,
        repository: 'mobile-app',
        branch: 'feature/component-library',
        targetBranch: 'development',
        conflicts: false,
        checks: { passed: 12, failed: 0, pending: 2 },
      },
      {
        id: '2',
        title: 'Fix authentication bug in login flow',
        description: 'Resolve issue with special characters in passwords',
        author: 'jane.smith',
        reviewers: ['john.doe'],
        status: 'open',
        createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        updatedAt: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
        additions: 85,
        deletions: 20,
        commits: 3,
        repository: 'mentor-app',
        branch: 'bugfix/auth-special-chars',
        targetBranch: 'main',
        conflicts: false,
        checks: { passed: 15, failed: 1, pending: 0 },
      },
      {
        id: '3',
        title: 'Implement advanced analytics charts',
        description: 'Add interactive charts for productivity metrics',
        author: 'alice.johnson',
        reviewers: ['bob.wilson', 'john.doe'],
        status: 'draft',
        createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
        updatedAt: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
        additions: 650,
        deletions: 120,
        commits: 5,
        repository: 'analytics-dashboard',
        branch: 'feature/advanced-charts',
        targetBranch: 'main',
        conflicts: true,
        checks: { passed: 8, failed: 3, pending: 4 },
      },
    ];
    setPullRequests(mockPRs);
  };

  const loadCodeMetrics = async () => {
    const mockMetrics: CodeMetrics = {
      codeQuality: {
        score: 85,
        bugs: 3,
        vulnerabilities: 1,
        codeSmells: 12,
        coverage: 78,
      },
      productivity: {
        commitsToday: 15,
        linesWritten: 2840,
        filesModified: 28,
        pullRequestsCreated: 4,
        pullRequestsReviewed: 7,
      },
      team: {
        activeContributors: 8,
        reviewTime: 2.5,
        mergeRate: 94,
      },
    };
    setCodeMetrics(mockMetrics);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
      case 'active':
        return '#4CAF50';
      case 'merged':
        return '#9C27B0';
      case 'closed':
      case 'archived':
        return '#757575';
      case 'draft':
        return '#FF9800';
      default:
        return '#2196F3';
    }
  };

  const getLanguageColor = (language: string) => {
    switch (language.toLowerCase()) {
      case 'typescript':
        return '#3178C6';
      case 'javascript':
        return '#F7DF1E';
      case 'python':
        return '#3776AB';
      case 'java':
        return '#ED8B00';
      case 'swift':
        return '#FA7343';
      default:
        return '#6B7280';
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getMetricsCards = (): MetricData[] => {
    if (!codeMetrics) return [];

    return [
      {
        id: 'quality',
        title: 'Code Quality',
        value: `${codeMetrics.codeQuality.score}%`,
        subtitle: `${codeMetrics.codeQuality.bugs} bugs, ${codeMetrics.codeQuality.vulnerabilities} vulnerabilities`,
        icon: 'code-tags-check',
        color: codeMetrics.codeQuality.score >= 80 ? '#4CAF50' : '#FF9800',
        progress: codeMetrics.codeQuality.score / 100,
        actionable: true,
      },
      {
        id: 'coverage',
        title: 'Test Coverage',
        value: `${codeMetrics.codeQuality.coverage}%`,
        icon: 'test-tube',
        color: codeMetrics.codeQuality.coverage >= 70 ? '#4CAF50' : '#F44336',
        progress: codeMetrics.codeQuality.coverage / 100,
        trend: 'up',
        trendValue: '+5%',
        actionable: true,
      },
      {
        id: 'commits',
        title: 'Commits Today',
        value: codeMetrics.productivity.commitsToday,
        icon: 'source-commit',
        color: '#2196F3',
        trend: 'up',
        trendValue: '+3',
        actionable: false,
      },
      {
        id: 'reviews',
        title: 'PRs Reviewed',
        value: codeMetrics.productivity.pullRequestsReviewed,
        subtitle: `${codeMetrics.productivity.pullRequestsCreated} created`,
        icon: 'source-pull',
        color: '#9C27B0',
        actionable: true,
      },
    ];
  };

  const renderRepositories = () => {
    const filteredRepos = repositories.filter(repo =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <View>
        {filteredRepos.map((repo) => (
          <Card key={repo.id} style={styles.repoCard}>
            <Card.Content>
              <View style={styles.repoHeader}>
                <View style={styles.repoInfo}>
                  <Title style={styles.repoName}>{repo.name}</Title>
                  <Paragraph style={styles.repoDescription}>{repo.description}</Paragraph>
                </View>
                <Chip
                  mode="outlined"
                  style={[styles.statusChip, { borderColor: getStatusColor(repo.status) }]}
                  textStyle={{ color: getStatusColor(repo.status) }}
                >
                  {repo.status.toUpperCase()}
                </Chip>
              </View>

              <View style={styles.repoMeta}>
                <View style={styles.repoMetaItem}>
                  <View style={[styles.languageDot, { backgroundColor: getLanguageColor(repo.language) }]} />
                  <Paragraph style={styles.metaText}>{repo.language}</Paragraph>
                </View>
                <View style={styles.repoMetaItem}>
                  <Icon name="star" size={14} color="#FFD700" />
                  <Paragraph style={styles.metaText}>{repo.stars}</Paragraph>
                </View>
                <View style={styles.repoMetaItem}>
                  <Icon name="source-fork" size={14} color="#757575" />
                  <Paragraph style={styles.metaText}>{repo.forks}</Paragraph>
                </View>
                <View style={styles.repoMetaItem}>
                  <Icon name="alert-circle" size={14} color="#F44336" />
                  <Paragraph style={styles.metaText}>{repo.openIssues}</Paragraph>
                </View>
              </View>

              <View style={styles.repoFooter}>
                <Paragraph style={styles.lastCommit}>
                  Last commit: {formatTimeAgo(repo.lastCommit)}
                </Paragraph>
                <Chip mode="flat" compact style={styles.branchChip}>
                  {repo.branch}
                </Chip>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>
    );
  };

  const renderPullRequests = () => {
    const filteredPRs = pullRequests.filter(pr =>
      pr.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pr.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pr.repository.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <View>
        {filteredPRs.map((pr) => (
          <Card key={pr.id} style={styles.prCard}>
            <Card.Content>
              <View style={styles.prHeader}>
                <View style={styles.prInfo}>
                  <Title style={styles.prTitle}>{pr.title}</Title>
                  <Paragraph style={styles.prDescription}>{pr.description}</Paragraph>
                  <View style={styles.prMeta}>
                    <Paragraph style={styles.prRepository}>{pr.repository}</Paragraph>
                    <Paragraph style={styles.prBranch}>
                      {pr.branch} → {pr.targetBranch}
                    </Paragraph>
                  </View>
                </View>
                <View style={styles.prStatus}>
                  <Chip
                    mode="outlined"
                    style={[styles.statusChip, { borderColor: getStatusColor(pr.status) }]}
                    textStyle={{ color: getStatusColor(pr.status) }}
                  >
                    {pr.status.toUpperCase()}
                  </Chip>
                  {pr.conflicts && (
                    <Chip mode="flat" style={styles.conflictChip} textStyle={{ color: '#F44336' }}>
                      CONFLICTS
                    </Chip>
                  )}
                </View>
              </View>

              <View style={styles.prStats}>
                <View style={styles.prStatItem}>
                  <Icon name="plus" size={12} color="#4CAF50" />
                  <Paragraph style={[styles.statText, { color: '#4CAF50' }]}>
                    +{pr.additions}
                  </Paragraph>
                </View>
                <View style={styles.prStatItem}>
                  <Icon name="minus" size={12} color="#F44336" />
                  <Paragraph style={[styles.statText, { color: '#F44336' }]}>
                    -{pr.deletions}
                  </Paragraph>
                </View>
                <View style={styles.prStatItem}>
                  <Icon name="source-commit" size={12} color="#757575" />
                  <Paragraph style={styles.statText}>{pr.commits} commits</Paragraph>
                </View>
              </View>

              <View style={styles.prChecks}>
                <View style={styles.checkItem}>
                  <Icon name="check-circle" size={12} color="#4CAF50" />
                  <Paragraph style={styles.checkText}>{pr.checks.passed}</Paragraph>
                </View>
                <View style={styles.checkItem}>
                  <Icon name="close-circle" size={12} color="#F44336" />
                  <Paragraph style={styles.checkText}>{pr.checks.failed}</Paragraph>
                </View>
                <View style={styles.checkItem}>
                  <Icon name="clock-outline" size={12} color="#FF9800" />
                  <Paragraph style={styles.checkText}>{pr.checks.pending}</Paragraph>
                </View>
              </View>

              <View style={styles.prFooter}>
                <View style={styles.prAuthor}>
                  <Avatar.Text size={24} label={pr.author.charAt(0).toUpperCase()} />
                  <Paragraph style={styles.authorText}>{pr.author}</Paragraph>
                </View>
                <Paragraph style={styles.prTime}>
                  Updated {formatTimeAgo(pr.updatedAt)}
                </Paragraph>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>
    );
  };

  const renderMetrics = () => {
    const metrics = getMetricsCards();
    return (
      <View style={styles.metricsContainer}>
        <View style={styles.metricsGrid}>
          {metrics.map((metric) => (
            <MetricCard
              key={metric.id}
              metric={metric}
              onPress={() => setShowMetricsModal(true)}
              size="medium"
            />
          ))}
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.Content title="Code" />
        <Appbar.Action icon="chart-line" onPress={() => setShowMetricsModal(true)} />
        <Appbar.Action icon="refresh" onPress={handleRefresh} />
      </Appbar.Header>

      <View style={styles.content}>
        {/* Search Bar */}
        <Searchbar
          placeholder="Search repositories and pull requests..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          style={styles.searchbar}
        />

        {/* Tab Navigation */}
        <SegmentedButtons
          value={activeTab}
          onValueChange={setActiveTab}
          buttons={[
            { value: 'repositories', label: `Repos (${repositories.length})`, icon: 'source-repository' },
            { value: 'pullrequests', label: `PRs (${pullRequests.length})`, icon: 'source-pull' },
            { value: 'metrics', label: 'Metrics', icon: 'chart-box' },
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
          {activeTab === 'repositories' && renderRepositories()}
          {activeTab === 'pullrequests' && renderPullRequests()}
          {activeTab === 'metrics' && renderMetrics()}
        </ScrollView>
      </View>

      {/* Floating Action Button */}
      <FAB
        style={styles.fab}
        icon="plus"
        onPress={() => {}}
        label="New PR"
      />

      {/* Metrics Modal */}
      <Portal>
        <Modal
          visible={showMetricsModal}
          onDismiss={() => setShowMetricsModal(false)}
          contentContainerStyle={styles.modalContent}
        >
          <Title>Code Quality Metrics</Title>
          {codeMetrics && (
            <ScrollView style={styles.modalScroll}>
              <View style={styles.metricSection}>
                <Paragraph style={styles.sectionTitle}>Quality Score</Paragraph>
                <Paragraph style={styles.sectionValue}>{codeMetrics.codeQuality.score}%</Paragraph>
                <Paragraph style={styles.sectionDetails}>
                  {codeMetrics.codeQuality.bugs} bugs • {codeMetrics.codeQuality.vulnerabilities} vulnerabilities • {codeMetrics.codeQuality.codeSmells} code smells
                </Paragraph>
              </View>

              <View style={styles.metricSection}>
                <Paragraph style={styles.sectionTitle}>Today's Activity</Paragraph>
                <Paragraph style={styles.sectionValue}>{codeMetrics.productivity.commitsToday} commits</Paragraph>
                <Paragraph style={styles.sectionDetails}>
                  {codeMetrics.productivity.linesWritten} lines written • {codeMetrics.productivity.filesModified} files modified
                </Paragraph>
              </View>

              <View style={styles.metricSection}>
                <Paragraph style={styles.sectionTitle}>Team Performance</Paragraph>
                <Paragraph style={styles.sectionValue}>{codeMetrics.team.mergeRate}% merge rate</Paragraph>
                <Paragraph style={styles.sectionDetails}>
                  {codeMetrics.team.activeContributors} contributors • {codeMetrics.team.reviewTime}h avg review time
                </Paragraph>
              </View>
            </ScrollView>
          )}
          <Button mode="contained" onPress={() => setShowMetricsModal(false)}>
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
            latency: 32,
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
  contentScroll: {
    flex: 1,
  },
  repoCard: {
    marginBottom: 12,
    elevation: 2,
  },
  repoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  repoInfo: {
    flex: 1,
    marginRight: 8,
  },
  repoName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  repoDescription: {
    fontSize: 12,
    opacity: 0.7,
    lineHeight: 16,
  },
  statusChip: {
    height: 24,
  },
  repoMeta: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  repoMetaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  languageDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
  metaText: {
    fontSize: 11,
    marginLeft: 2,
  },
  repoFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  lastCommit: {
    fontSize: 10,
    opacity: 0.6,
  },
  branchChip: {
    height: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
  },
  prCard: {
    marginBottom: 12,
    elevation: 2,
  },
  prHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  prInfo: {
    flex: 1,
    marginRight: 8,
  },
  prTitle: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  prDescription: {
    fontSize: 11,
    opacity: 0.7,
    lineHeight: 14,
    marginBottom: 4,
  },
  prMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  prRepository: {
    fontSize: 10,
    fontWeight: '500',
    marginRight: 8,
  },
  prBranch: {
    fontSize: 10,
    opacity: 0.6,
  },
  prStatus: {
    alignItems: 'flex-end',
  },
  conflictChip: {
    height: 20,
    backgroundColor: 'rgba(244, 67, 54, 0.1)',
    marginTop: 4,
  },
  prStats: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  prStatItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
  },
  statText: {
    fontSize: 10,
    marginLeft: 2,
  },
  prChecks: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  checkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 8,
  },
  checkText: {
    fontSize: 10,
    marginLeft: 2,
  },
  prFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  prAuthor: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  authorText: {
    fontSize: 10,
    marginLeft: 6,
  },
  prTime: {
    fontSize: 10,
    opacity: 0.6,
  },
  metricsContainer: {
    flex: 1,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
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
  modalScroll: {
    marginVertical: 16,
  },
  metricSection: {
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
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  sectionDetails: {
    fontSize: 11,
    opacity: 0.7,
  },
});

export default CodeScreen;
