/**
 * Tasks Slice - Task management state
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { TaskData } from '../../components/TaskQuickView';

export interface TasksState {
  tasks: TaskData[];
  filteredTasks: TaskData[];
  filters: {
    status: TaskData['status'][];
    priority: TaskData['priority'][];
    type: TaskData['type'][];
    assignee: string[];
    tags: string[];
  };
  searchQuery: string;
  sortBy: 'dueDate' | 'priority' | 'status' | 'title' | 'createdAt';
  sortOrder: 'asc' | 'desc';
  loading: boolean;
  selectedTaskId: string | null;
  showCompleted: boolean;
}

const initialState: TasksState = {
  tasks: [],
  filteredTasks: [],
  filters: {
    status: [],
    priority: [],
    type: [],
    assignee: [],
    tags: [],
  },
  searchQuery: '',
  sortBy: 'dueDate',
  sortOrder: 'asc',
  loading: false,
  selectedTaskId: null,
  showCompleted: false,
};

const tasksSlice = createSlice({
  name: 'tasks',
  initialState,
  reducers: {
    setTasks: (state, action: PayloadAction<TaskData[]>) => {
      state.tasks = action.payload;
      tasksSlice.caseReducers.applyFilters(state);
    },
    addTask: (state, action: PayloadAction<TaskData>) => {
      state.tasks.push(action.payload);
      tasksSlice.caseReducers.applyFilters(state);
    },
    updateTask: (state, action: PayloadAction<TaskData>) => {
      const index = state.tasks.findIndex(task => task.id === action.payload.id);
      if (index !== -1) {
        state.tasks[index] = action.payload;
        tasksSlice.caseReducers.applyFilters(state);
      }
    },
    deleteTask: (state, action: PayloadAction<string>) => {
      state.tasks = state.tasks.filter(task => task.id !== action.payload);
      tasksSlice.caseReducers.applyFilters(state);
    },
    updateTaskStatus: (state, action: PayloadAction<{
      taskId: string;
      status: TaskData['status'];
    }>) => {
      const task = state.tasks.find(t => t.id === action.payload.taskId);
      if (task) {
        task.status = action.payload.status;
        if (action.payload.status === 'completed') {
          // Set actual time if not already set
          if (!task.actualTime && task.estimatedTime) {
            task.actualTime = task.estimatedTime;
          }
        }
        tasksSlice.caseReducers.applyFilters(state);
      }
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
      tasksSlice.caseReducers.applyFilters(state);
    },
    setFilters: (state, action: PayloadAction<Partial<TasksState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
      tasksSlice.caseReducers.applyFilters(state);
    },
    setSortBy: (state, action: PayloadAction<TasksState['sortBy']>) => {
      state.sortBy = action.payload;
      tasksSlice.caseReducers.applyFilters(state);
    },
    setSortOrder: (state, action: PayloadAction<TasksState['sortOrder']>) => {
      state.sortOrder = action.payload;
      tasksSlice.caseReducers.applyFilters(state);
    },
    setSelectedTask: (state, action: PayloadAction<string | null>) => {
      state.selectedTaskId = action.payload;
    },
    setShowCompleted: (state, action: PayloadAction<boolean>) => {
      state.showCompleted = action.payload;
      tasksSlice.caseReducers.applyFilters(state);
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
      state.searchQuery = '';
      tasksSlice.caseReducers.applyFilters(state);
    },
    applyFilters: (state) => {
      let filtered = [...state.tasks];

      // Apply search query
      if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase();
        filtered = filtered.filter(task =>
          task.title.toLowerCase().includes(query) ||
          task.description?.toLowerCase().includes(query) ||
          task.tags?.some(tag => tag.toLowerCase().includes(query))
        );
      }

      // Apply status filter
      if (state.filters.status.length > 0) {
        filtered = filtered.filter(task => state.filters.status.includes(task.status));
      }

      // Apply priority filter
      if (state.filters.priority.length > 0) {
        filtered = filtered.filter(task => state.filters.priority.includes(task.priority));
      }

      // Apply type filter
      if (state.filters.type.length > 0) {
        filtered = filtered.filter(task => state.filters.type.includes(task.type));
      }

      // Apply assignee filter
      if (state.filters.assignee.length > 0 && state.filters.assignee[0] !== '') {
        filtered = filtered.filter(task => 
          task.assignee && state.filters.assignee.includes(task.assignee)
        );
      }

      // Apply tags filter
      if (state.filters.tags.length > 0) {
        filtered = filtered.filter(task =>
          task.tags?.some(tag => state.filters.tags.includes(tag))
        );
      }

      // Show/hide completed tasks
      if (!state.showCompleted) {
        filtered = filtered.filter(task => task.status !== 'completed');
      }

      // Apply sorting
      filtered.sort((a, b) => {
        let aValue: any, bValue: any;

        switch (state.sortBy) {
          case 'dueDate':
            aValue = a.dueDate ? new Date(a.dueDate).getTime() : Infinity;
            bValue = b.dueDate ? new Date(b.dueDate).getTime() : Infinity;
            break;
          case 'priority':
            const priorityOrder = { low: 0, medium: 1, high: 2, urgent: 3 };
            aValue = priorityOrder[a.priority];
            bValue = priorityOrder[b.priority];
            break;
          case 'status':
            const statusOrder = { pending: 0, in_progress: 1, review: 2, completed: 3 };
            aValue = statusOrder[a.status];
            bValue = statusOrder[b.status];
            break;
          case 'title':
            aValue = a.title.toLowerCase();
            bValue = b.title.toLowerCase();
            break;
          default:
            aValue = 0;
            bValue = 0;
        }

        if (state.sortOrder === 'asc') {
          return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
        } else {
          return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
        }
      });

      state.filteredTasks = filtered;
    },
  },
});

export const {
  setTasks,
  addTask,
  updateTask,
  deleteTask,
  updateTaskStatus,
  setSearchQuery,
  setFilters,
  setSortBy,
  setSortOrder,
  setSelectedTask,
  setShowCompleted,
  setLoading,
  clearFilters,
} = tasksSlice.actions;

export default tasksSlice.reducer;
