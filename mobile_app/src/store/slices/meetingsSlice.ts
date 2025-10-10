/**
 * Meetings Slice - Meeting management state
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { MeetingData } from '../../components/MeetingPreview';

export interface MeetingsState {
  meetings: MeetingData[];
  upcomingMeetings: MeetingData[];
  pastMeetings: MeetingData[];
  currentMeeting: MeetingData | null;
  searchQuery: string;
  filters: {
    attendees: string[];
    meetingTypes: string[];
    dateRange: {
      start: Date | null;
      end: Date | null;
    };
  };
  loading: boolean;
  selectedMeetingId: string | null;
  preparationReminders: boolean;
  autoJoin: boolean;
}

const initialState: MeetingsState = {
  meetings: [],
  upcomingMeetings: [],
  pastMeetings: [],
  currentMeeting: null,
  searchQuery: '',
  filters: {
    attendees: [],
    meetingTypes: [],
    dateRange: {
      start: null,
      end: null,
    },
  },
  loading: false,
  selectedMeetingId: null,
  preparationReminders: true,
  autoJoin: false,
};

const meetingsSlice = createSlice({
  name: 'meetings',
  initialState,
  reducers: {
    setMeetings: (state, action: PayloadAction<MeetingData[]>) => {
      state.meetings = action.payload;
      meetingsSlice.caseReducers.categorizeMeetings(state);
    },
    addMeeting: (state, action: PayloadAction<MeetingData>) => {
      state.meetings.push(action.payload);
      meetingsSlice.caseReducers.categorizeMeetings(state);
    },
    updateMeeting: (state, action: PayloadAction<MeetingData>) => {
      const index = state.meetings.findIndex(meeting => meeting.id === action.payload.id);
      if (index !== -1) {
        state.meetings[index] = action.payload;
        meetingsSlice.caseReducers.categorizeMeetings(state);
      }
    },
    deleteMeeting: (state, action: PayloadAction<string>) => {
      state.meetings = state.meetings.filter(meeting => meeting.id !== action.payload);
      meetingsSlice.caseReducers.categorizeMeetings(state);
    },
    updatePreparationStatus: (state, action: PayloadAction<{
      meetingId: string;
      preparationStatus: MeetingData['preparationStatus'];
    }>) => {
      const meeting = state.meetings.find(m => m.id === action.payload.meetingId);
      if (meeting) {
        meeting.preparationStatus = action.payload.preparationStatus;
        meetingsSlice.caseReducers.categorizeMeetings(state);
      }
    },
    setCurrentMeeting: (state, action: PayloadAction<MeetingData | null>) => {
      state.currentMeeting = action.payload;
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
      meetingsSlice.caseReducers.applyFilters(state);
    },
    setFilters: (state, action: PayloadAction<Partial<MeetingsState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
      meetingsSlice.caseReducers.applyFilters(state);
    },
    setSelectedMeeting: (state, action: PayloadAction<string | null>) => {
      state.selectedMeetingId = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setPreparationReminders: (state, action: PayloadAction<boolean>) => {
      state.preparationReminders = action.payload;
    },
    setAutoJoin: (state, action: PayloadAction<boolean>) => {
      state.autoJoin = action.payload;
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
      state.searchQuery = '';
      meetingsSlice.caseReducers.applyFilters(state);
    },
    categorizeMeetings: (state) => {
      const now = new Date();
      const upcoming: MeetingData[] = [];
      const past: MeetingData[] = [];

      state.meetings.forEach(meeting => {
        if (new Date(meeting.startTime) > now) {
          upcoming.push(meeting);
        } else {
          past.push(meeting);
        }
      });

      // Sort upcoming by start time (soonest first)
      upcoming.sort((a, b) => 
        new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
      );

      // Sort past by start time (most recent first)
      past.sort((a, b) => 
        new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
      );

      state.upcomingMeetings = upcoming;
      state.pastMeetings = past;
    },
    applyFilters: (state) => {
      // This would filter meetings based on current filters
      // For now, we'll just call categorize which handles the basic filtering
      meetingsSlice.caseReducers.categorizeMeetings(state);
    },
    generatePreparationTasks: (state, action: PayloadAction<string>) => {
      const meeting = state.meetings.find(m => m.id === action.payload);
      if (meeting && !meeting.preparationStatus.isComplete) {
        // Generate AI-powered preparation suggestions
        const suggestions = [
          'Review meeting agenda and objectives',
          'Prepare talking points and questions',
          'Gather relevant documents and data',
          'Check technical setup (camera, microphone)',
          'Review attendee backgrounds and roles',
        ];

        // Add meeting-type specific suggestions
        if (meeting.aiInsights) {
          switch (meeting.aiInsights.meetingType) {
            case 'standup':
              suggestions.push('Prepare status updates', 'Note any blockers');
              break;
            case 'planning':
              suggestions.push('Review backlog items', 'Prepare estimates');
              break;
            case 'review':
              suggestions.push('Prepare demo materials', 'Gather feedback questions');
              break;
            case 'interview':
              suggestions.push('Review candidate resume', 'Prepare interview questions');
              break;
          }
        }

        meeting.preparationStatus.suggestions = suggestions;
        meeting.preparationStatus.totalItems = suggestions.length;
      }
    },
  },
});

export const {
  setMeetings,
  addMeeting,
  updateMeeting,
  deleteMeeting,
  updatePreparationStatus,
  setCurrentMeeting,
  setSearchQuery,
  setFilters,
  setSelectedMeeting,
  setLoading,
  setPreparationReminders,
  setAutoJoin,
  clearFilters,
  generatePreparationTasks,
} = meetingsSlice.actions;

export default meetingsSlice.reducer;
