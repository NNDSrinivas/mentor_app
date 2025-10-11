/**
 * Tasks Screen - Comprehensive task management interface
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
  Menu,
  Divider,
} from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';

import { TaskQuickView, MetricCard, StatusIndicator } from '../components';
import type { TaskData } from '../components/TaskQuickView';
import type { MetricData } from '../components/MetricCard';
import type { RootState } from '../store';
import {
  setTasks,
  updateTaskStatus,
  setSearchQuery,
  setFilters,
  setSortBy,
  setSortOrder,
  setShowCompleted,
  setLoading,
  clearFilters,
} from '../store/slices/tasksSlice';

const TasksScreen: React.FC = () => {
  const dispatch = useDispatch();
  const {
    filteredTasks,
    filters,
    searchQuery,
    sortBy,
    sortOrder,
    showCompleted,
    loading,
  } = useSelector((state: RootState) => state.tasks);

  const [activeView, setActiveView] = useState('list');
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      loadTasks();
    }, [])
  );

  const loadTasks = async () => {
    dispatch(setLoading(true));
    try {
      // Simulate API call to load tasks
      const mockTasks: TaskData[] = [
        {
          id: '1',
          title: 'Fix login authentication bug',
          description: 'Users unable to login with special characters in password',
          priority: 'urgent',
          status: 'in_progress',
          dueDate: new Date(Date.now() + 24 * 60 * 60 * 1000), // Tomorrow
          assignee: 'John Doe',
          tags: ['bug', 'authentication', 'urgent'],
          estimatedTime: 120, // 2 hours
          actualTime: 90, // 1.5 hours so far
          type: 'bug',
        },
        {
          id: '2',
          title: 'Implement dark mode toggle',
          description: 'Add user preference for dark/light theme switching',
          priority: 'medium',
          status: 'pending',
          dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // Next week
          assignee: 'Jane Smith',
          tags: ['feature', 'ui', 'enhancement'],
          estimatedTime: 240, // 4 hours
          type: 'feature',
        },
        {
          id: '3',
          title: 'Update API documentation',
          description: 'Document new endpoints and update examples',
          priority: 'low',
          status: 'review',
          dueDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // In 3 days
          assignee: 'Alice Johnson',
          tags: ['documentation', 'api'],
          estimatedTime: 180, // 3 hours
          actualTime: 180, // Completed
          type: 'task',
        },
        {
          id: '4',
          title: 'Optimize database queries',
          description: 'Improve performance of user data retrieval',
          priority: 'high',
          status: 'completed',
          assignee: 'Bob Wilson',
          tags: ['performance', 'database', 'optimization'],
          estimatedTime: 300, // 5 hours
          actualTime: 360, // 6 hours (over estimate)
          type: 'improvement',
        },
      ];

      dispatch(setTasks(mockTasks));
    } catch (error) {
      console.error('Error loading tasks:', error);
      Alert.alert('Error', 'Failed to load tasks');
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadTasks();
    setRefreshing(false);
  };

  const handleTaskStatusChange = (taskId: string, newStatus: TaskData['status']) => {
    dispatch(updateTaskStatus({ taskId, status: newStatus }));
  };

  const getTaskMetrics = (): MetricData[] => {
    const totalTasks = filteredTasks.length;
    const completedTasks = filteredTasks.filter(t => t.status === 'completed').length;
    const inProgressTasks = filteredTasks.filter(t => t.status === 'in_progress').length;
    const overdueTasks = filteredTasks.filter(t => 
      t.dueDate && new Date(t.dueDate) < new Date() && t.status !== 'completed'
    ).length;

    const completionRate = totalTasks > 0 ? completedTasks / totalTasks : 0;

    return [
      {
        id: 'total',
        title: 'Total Tasks',
        value: totalTasks,
        icon: 'format-list-checks',
        color: '#2196F3',
        actionable: false,
      },
      {
        id: 'completed',
        title: 'Completed',
        value: completedTasks,
        icon: 'check-circle',
        color: '#4CAF50',
        progress: completionRate,
        trend: 'up',
        trendValue: '+12%',
        actionable: true,
      },
      {
        id: 'in_progress',
        title: 'In Progress',
        value: inProgressTasks,
        icon: 'clock-outline',
        color: '#FF9800',
        actionable: true,
      },
      {
        id: 'overdue',
        title: 'Overdue',
        value: overdueTasks,
        icon: 'alert-circle',
        color: overdueTasks > 0 ? '#F44336' : '#4CAF50',
        trend: overdueTasks > 0 ? 'up' : 'stable',
        trendValue: overdueTasks > 0 ? `${overdueTasks} tasks` : 'None',
        actionable: overdueTasks > 0,
      },
    ];
  };

  const renderTaskList = () => {
    if (filteredTasks.length === 0) {
      return (
        <Surface style={styles.emptyState}>
          <Title>No tasks found</Title>
          <Paragraph>
            {searchQuery || Object.values(filters).some(f => f.length > 0)
              ? 'Try adjusting your filters or search terms.'
              : 'You have no tasks. Create your first task to get started.'}
          </Paragraph>
          {(searchQuery || Object.values(filters).some(f => f.length > 0)) && (
            <Button
              mode="outlined"
              onPress={() => dispatch(clearFilters())}
              style={styles.clearFiltersButton}
            >
              Clear Filters
            </Button>
          )}
        </Surface>
      );
    }

    return filteredTasks.map((task) => (
      <TaskQuickView
        key={task.id}
        task={task}
        onPress={() => {}}
        onStatusChange={handleTaskStatusChange}
        showActions={true}
        compact={false}
      />
    ));
  };

  const renderMetricsView = () => {
    const metrics = getTaskMetrics();
    
    return (
      <View style={styles.metricsGrid}>
        {metrics.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            onPress={() => {}}
            size="medium"
          />
        ))}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.Content title="Tasks" />
        <Appbar.Action 
          icon="sort" 
          onPress={() => setShowSortMenu(true)} 
        />
        <Appbar.Action 
          icon="filter-variant" 
          onPress={() => setShowFilterModal(true)} 
        />
      </Appbar.Header>

      <View style={styles.content}>
        {/* Search Bar */}
        <Searchbar
          placeholder="Search tasks..."
          onChangeText={(query) => dispatch(setSearchQuery(query))}
          value={searchQuery}
          style={styles.searchbar}
        />

        {/* View Toggle */}
        <SegmentedButtons
          value={activeView}
          onValueChange={setActiveView}
          buttons={[
            { value: 'list', label: 'List', icon: 'format-list-bulleted' },
            { value: 'metrics', label: 'Metrics', icon: 'chart-box' },
          ]}
          style={styles.viewToggle}
        />

        {/* Quick Filters */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.quickFilters}
        >
          <Chip
            icon="eye"
            selected={showCompleted}
            onPress={() => dispatch(setShowCompleted(!showCompleted))}
            style={styles.filterChip}
          >
            Show Completed
          </Chip>
          <Chip
            icon="alert-circle"
            onPress={() => dispatch(setFilters({ priority: ['urgent', 'high'] }))}
            style={styles.filterChip}
          >
            High Priority
          </Chip>
          <Chip
            icon="clock-alert"
            onPress={() => {
              // Filter for overdue tasks
              const today = new Date();
              // This would need custom filter logic
            }}
            style={styles.filterChip}
          >
            Overdue
          </Chip>
          <Chip
            icon="account"
            onPress={() => {}}
            style={styles.filterChip}
          >
            My Tasks
          </Chip>
        </ScrollView>

        {/* Content */}
        <ScrollView
          style={styles.contentScroll}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          }
          showsVerticalScrollIndicator={false}
        >
          {activeView === 'list' ? renderTaskList() : renderMetricsView()}
        </ScrollView>
      </View>

      {/* Floating Action Button */}
      <FAB
        style={styles.fab}
        icon="plus"
        onPress={() => {}}
        label="New Task"
      />

      {/* Sort Menu */}
      <Menu
        visible={showSortMenu}
        onDismiss={() => setShowSortMenu(false)}
        anchor={<View />}
        anchorPosition="top"
      >
        <Menu.Item
          onPress={() => {
            dispatch(setSortBy('dueDate'));
            setShowSortMenu(false);
          }}
          title="Due Date"
          leadingIcon="calendar"
        />
        <Menu.Item
          onPress={() => {
            dispatch(setSortBy('priority'));
            setShowSortMenu(false);
          }}
          title="Priority"
          leadingIcon="flag"
        />
        <Menu.Item
          onPress={() => {
            dispatch(setSortBy('status'));
            setShowSortMenu(false);
          }}
          title="Status"
          leadingIcon="check-circle"
        />
        <Menu.Item
          onPress={() => {
            dispatch(setSortBy('title'));
            setShowSortMenu(false);
          }}
          title="Title"
          leadingIcon="alphabetical"
        />
        <Divider />
        <Menu.Item
          onPress={() => {
            dispatch(setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc'));
            setShowSortMenu(false);
          }}
          title={`Order: ${sortOrder === 'asc' ? 'Ascending' : 'Descending'}`}
          leadingIcon={sortOrder === 'asc' ? 'sort-ascending' : 'sort-descending'}
        />
      </Menu>

      {/* Filter Modal */}
      <Portal>
        <Modal
          visible={showFilterModal}
          onDismiss={() => setShowFilterModal(false)}
          contentContainerStyle={styles.modalContent}
        >
          <Title>Filter Tasks</Title>
          <Paragraph style={styles.modalSubtitle}>
            Customize your task view
          </Paragraph>

          {/* Status Filters */}
          <View style={styles.filterSection}>
            <Paragraph style={styles.filterSectionTitle}>Status</Paragraph>
            <View style={styles.filterChips}>
              {(['pending', 'in_progress', 'review', 'completed'] as TaskData['status'][]).map((status) => (
                <Chip
                  key={status}
                  mode={filters.status.includes(status) ? 'flat' : 'outlined'}
                  selected={filters.status.includes(status)}
                  onPress={() => {
                    const newStatuses = filters.status.includes(status)
                      ? filters.status.filter(s => s !== status)
                      : [...filters.status, status];
                    dispatch(setFilters({ status: newStatuses }));
                  }}
                  style={styles.filterChipModal}
                >
                  {status.replace('_', ' ').toUpperCase()}
                </Chip>
              ))}
            </View>
          </View>

          {/* Priority Filters */}
          <View style={styles.filterSection}>
            <Paragraph style={styles.filterSectionTitle}>Priority</Paragraph>
            <View style={styles.filterChips}>
              {(['low', 'medium', 'high', 'urgent'] as TaskData['priority'][]).map((priority) => (
                <Chip
                  key={priority}
                  mode={filters.priority.includes(priority) ? 'flat' : 'outlined'}
                  selected={filters.priority.includes(priority)}
                  onPress={() => {
                    const newPriorities = filters.priority.includes(priority)
                      ? filters.priority.filter(p => p !== priority)
                      : [...filters.priority, priority];
                    dispatch(setFilters({ priority: newPriorities }));
                  }}
                  style={styles.filterChipModal}
                >
                  {priority.toUpperCase()}
                </Chip>
              ))}
            </View>
          </View>

          {/* Type Filters */}
          <View style={styles.filterSection}>
            <Paragraph style={styles.filterSectionTitle}>Type</Paragraph>
            <View style={styles.filterChips}>
              {(['bug', 'feature', 'task', 'improvement'] as TaskData['type'][]).map((type) => (
                <Chip
                  key={type}
                  mode={filters.type.includes(type) ? 'flat' : 'outlined'}
                  selected={filters.type.includes(type)}
                  onPress={() => {
                    const newTypes = filters.type.includes(type)
                      ? filters.type.filter(t => t !== type)
                      : [...filters.type, type];
                    dispatch(setFilters({ type: newTypes }));
                  }}
                  style={styles.filterChipModal}
                >
                  {type.toUpperCase()}
                </Chip>
              ))}
            </View>
          </View>

          <View style={styles.modalActions}>
            <Button onPress={() => dispatch(clearFilters())}>
              Clear All
            </Button>
            <Button 
              mode="contained" 
              onPress={() => setShowFilterModal(false)}
            >
              Apply Filters
            </Button>
          </View>
        </Modal>
      </Portal>

      {/* Status Indicator */}
      <StatusIndicator
        status={{
          connection: {
            status: 'connected',
            quality: 'good',
            latency: 68,
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
  viewToggle: {
    marginBottom: 16,
  },
  quickFilters: {
    marginBottom: 16,
    maxHeight: 40,
  },
  filterChip: {
    marginRight: 8,
  },
  contentScroll: {
    flex: 1,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  emptyState: {
    padding: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
  },
  clearFiltersButton: {
    marginTop: 16,
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
  filterSection: {
    marginBottom: 20,
  },
  filterSectionTitle: {
    fontWeight: 'bold',
    marginBottom: 8,
    fontSize: 14,
  },
  filterChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  filterChipModal: {
    marginRight: 8,
    marginBottom: 8,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 16,
  },
});

export default TasksScreen;
