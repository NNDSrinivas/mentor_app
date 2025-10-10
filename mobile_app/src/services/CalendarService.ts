/**
 * Calendar Service - Advanced calendar integration with intelligent scheduling
 * Handles calendar events, meeting preparation, and smart notifications
 */

import { CalendarEvents } from '@react-native-calendar-events/calendar-events';
import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';
import BackgroundTimer from 'react-native-background-timer';

interface CalendarEvent {
  id: string;
  title: string;
  startDate: Date;
  endDate: Date;
  location?: string;
  notes?: string;
  attendees?: Array<{
    name: string;
    email: string;
    status: 'accepted' | 'declined' | 'tentative' | 'pending';
  }>;
  url?: string;
  calendarId: string;
  isAllDay: boolean;
  recurrence?: string;
  alarms?: Array<{
    date: Date;
    relativeOffset?: number;
  }>;
}

interface MeetingPreparation {
  eventId: string;
  context: {
    participants: string[];
    agenda: string[];
    previousMeetings: any[];
    relatedTasks: any[];
    relatedCode: any[];
  };
  aiSuggestions: {
    topics: string[];
    questions: string[];
    materials: string[];
  };
  preparationScore: number;
  lastUpdated: Date;
}

interface CalendarInsights {
  meetingHours: number;
  focusTime: number;
  overlapCount: number;
  travelTime: number;
  preparationTime: number;
  efficiency: number;
}

export class CalendarService {
  private isInitialized: boolean = false;
  private monitoringInterval: any;
  private events: CalendarEvent[] = [];
  private preparations: Map<string, MeetingPreparation> = new Map();
  private calendars: any[] = [];
  private permissions: {
    read: boolean;
    write: boolean;
  } = { read: false, write: false };

  async initialize(): Promise<void> {
    try {
      // Request calendar permissions
      await this.requestPermissions();

      // Load available calendars
      await this.loadCalendars();

      // Load existing events
      await this.loadEvents();

      // Load meeting preparations
      await this.loadMeetingPreparations();

      this.isInitialized = true;
      console.log('Calendar Service initialized');
    } catch (error) {
      console.error('Calendar Service initialization error:', error);
      throw error;
    }
  }

  private async requestPermissions(): Promise<void> {
    try {
      // Request read permission
      const readStatus = await CalendarEvents.requestPermissions();
      this.permissions.read = readStatus === 'authorized';

      // Request write permission
      const writeStatus = await CalendarEvents.requestPermissions(true);
      this.permissions.write = writeStatus === 'authorized';

      if (!this.permissions.read) {
        throw new Error('Calendar read permission denied');
      }

      console.log('Calendar permissions:', this.permissions);
    } catch (error) {
      console.error('Calendar permissions error:', error);
      throw error;
    }
  }

  private async loadCalendars(): Promise<void> {
    if (!this.permissions.read) return;

    try {
      this.calendars = await CalendarEvents.findCalendars();
      console.log(`Loaded ${this.calendars.length} calendars`);
    } catch (error) {
      console.error('Failed to load calendars:', error);
    }
  }

  private async loadEvents(): Promise<void> {
    if (!this.permissions.read) return;

    try {
      const startDate = new Date();
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 30); // Next 30 days

      const events = await CalendarEvents.fetchAllEvents(
        startDate.toISOString(),
        endDate.toISOString(),
        this.calendars.map(cal => cal.id)
      );

      this.events = events.map(event => ({
        id: event.id,
        title: event.title,
        startDate: new Date(event.startDate),
        endDate: new Date(event.endDate),
        location: event.location,
        notes: event.notes,
        attendees: event.attendees?.map(att => ({
          name: att.name || '',
          email: att.email || '',
          status: att.participantStatus as any || 'pending',
        })) || [],
        url: event.url,
        calendarId: event.calendar?.id || '',
        isAllDay: event.allDay || false,
        recurrence: event.recurrence,
        alarms: event.alarms?.map(alarm => ({
          date: new Date(alarm.date),
          relativeOffset: alarm.relativeOffset,
        })) || [],
      }));

      console.log(`Loaded ${this.events.length} calendar events`);
    } catch (error) {
      console.error('Failed to load events:', error);
    }
  }

  private async loadMeetingPreparations(): Promise<void> {
    try {
      const preparationsData = await AsyncStorage.getItem('meeting_preparations');
      if (preparationsData) {
        const preparations = JSON.parse(preparationsData);
        this.preparations = new Map(Object.entries(preparations));
      }
    } catch (error) {
      console.error('Failed to load meeting preparations:', error);
    }
  }

  private async saveMeetingPreparations(): Promise<void> {
    try {
      const preparationsObj = Object.fromEntries(this.preparations);
      await AsyncStorage.setItem('meeting_preparations', JSON.stringify(preparationsObj));
    } catch (error) {
      console.error('Failed to save meeting preparations:', error);
    }
  }

  async refreshUpcomingEvents(): Promise<void> {
    if (!this.permissions.read) return;

    try {
      await this.loadEvents();
      
      // Prepare upcoming meetings
      const upcomingEvents = this.getUpcomingEvents(24); // Next 24 hours
      for (const event of upcomingEvents) {
        if (this.isMeeting(event)) {
          await this.prepareMeeting(event);
        }
      }
    } catch (error) {
      console.error('Failed to refresh upcoming events:', error);
    }
  }

  async syncCalendarEvents(): Promise<void> {
    try {
      await this.loadEvents();
      
      // Sync with backend
      const syncData = {
        events: this.events.map(event => ({
          ...event,
          startDate: event.startDate.toISOString(),
          endDate: event.endDate.toISOString(),
        })),
        lastSync: new Date().toISOString(),
      };
      
      await AsyncStorage.setItem('calendar_sync_data', JSON.stringify(syncData));
    } catch (error) {
      console.error('Calendar sync error:', error);
    }
  }

  getUpcomingEvents(hours: number = 24): CalendarEvent[] {
    const now = new Date();
    const cutoff = new Date(now.getTime() + hours * 60 * 60 * 1000);
    
    return this.events
      .filter(event => event.startDate >= now && event.startDate <= cutoff)
      .sort((a, b) => a.startDate.getTime() - b.startDate.getTime());
  }

  getEventsForDay(date: Date): CalendarEvent[] {
    const startOfDay = new Date(date);
    startOfDay.setHours(0, 0, 0, 0);
    
    const endOfDay = new Date(date);
    endOfDay.setHours(23, 59, 59, 999);
    
    return this.events.filter(event => 
      event.startDate >= startOfDay && event.startDate <= endOfDay
    );
  }

  private isMeeting(event: CalendarEvent): boolean {
    // Determine if event is a meeting based on various criteria
    const meetingKeywords = [
      'meeting', 'call', 'sync', 'standup', 'review', 'discussion',
      'interview', 'demo', 'presentation', 'planning', 'retrospective'
    ];
    
    const title = event.title.toLowerCase();
    const hasKeyword = meetingKeywords.some(keyword => title.includes(keyword));
    const hasAttendees = event.attendees && event.attendees.length > 0;
    const hasUrl = event.url && (
      event.url.includes('zoom') || 
      event.url.includes('meet') || 
      event.url.includes('teams')
    );
    
    return hasKeyword || hasAttendees || hasUrl;
  }

  async prepareMeeting(event: CalendarEvent): Promise<MeetingPreparation> {
    try {
      let preparation = this.preparations.get(event.id);
      
      if (!preparation || this.shouldUpdatePreparation(preparation)) {
        preparation = await this.generateMeetingPreparation(event);
        this.preparations.set(event.id, preparation);
        await this.saveMeetingPreparations();
      }
      
      return preparation;
    } catch (error) {
      console.error('Meeting preparation error:', error);
      throw error;
    }
  }

  async prepareMeetingContext(meetingId: string): Promise<MeetingPreparation | null> {
    const event = this.events.find(e => e.id === meetingId);
    if (!event) return null;
    
    return await this.prepareMeeting(event);
  }

  private shouldUpdatePreparation(preparation: MeetingPreparation): boolean {
    const hoursSinceUpdate = (Date.now() - preparation.lastUpdated.getTime()) / (1000 * 60 * 60);
    return hoursSinceUpdate > 6; // Update every 6 hours
  }

  private async generateMeetingPreparation(event: CalendarEvent): Promise<MeetingPreparation> {
    try {
      // Extract participants
      const participants = event.attendees?.map(att => att.email) || [];
      
      // Find related data
      const [previousMeetings, relatedTasks, relatedCode] = await Promise.all([
        this.findPreviousMeetings(event),
        this.findRelatedTasks(event),
        this.findRelatedCode(event),
      ]);
      
      // Generate AI suggestions
      const aiSuggestions = await this.generateAISuggestions(event, {
        previousMeetings,
        relatedTasks,
        relatedCode,
      });
      
      // Calculate preparation score
      const preparationScore = this.calculatePreparationScore(event, {
        previousMeetings,
        relatedTasks,
        relatedCode,
        aiSuggestions,
      });
      
      return {
        eventId: event.id,
        context: {
          participants,
          agenda: this.extractAgenda(event),
          previousMeetings,
          relatedTasks,
          relatedCode,
        },
        aiSuggestions,
        preparationScore,
        lastUpdated: new Date(),
      };
    } catch (error) {
      console.error('Meeting preparation generation error:', error);
      throw error;
    }
  }

  private async findPreviousMeetings(event: CalendarEvent): Promise<any[]> {
    try {
      // Find meetings with similar participants or titles
      const similarities = this.events
        .filter(e => e.id !== event.id && e.endDate < new Date())
        .map(e => ({
          event: e,
          similarity: this.calculateEventSimilarity(event, e),
        }))
        .filter(s => s.similarity > 0.3)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, 5);
      
      return similarities.map(s => s.event);
    } catch (error) {
      console.error('Previous meetings search error:', error);
      return [];
    }
  }

  private async findRelatedTasks(event: CalendarEvent): Promise<any[]> {
    try {
      const tasksData = await AsyncStorage.getItem('tasks');
      if (!tasksData) return [];
      
      const tasks = JSON.parse(tasksData);
      const keywords = this.extractKeywords(event.title + ' ' + (event.notes || ''));
      
      return tasks.filter((task: any) => {
        const taskText = (task.title + ' ' + (task.description || '')).toLowerCase();
        return keywords.some(keyword => taskText.includes(keyword.toLowerCase()));
      }).slice(0, 10);
    } catch (error) {
      console.error('Related tasks search error:', error);
      return [];
    }
  }

  private async findRelatedCode(event: CalendarEvent): Promise<any[]> {
    try {
      const codeData = await AsyncStorage.getItem('code_data');
      if (!codeData) return [];
      
      const code = JSON.parse(codeData);
      const keywords = this.extractKeywords(event.title + ' ' + (event.notes || ''));
      
      return code.filter((item: any) => {
        const codeText = (item.title + ' ' + (item.description || '')).toLowerCase();
        return keywords.some(keyword => codeText.includes(keyword.toLowerCase()));
      }).slice(0, 5);
    } catch (error) {
      console.error('Related code search error:', error);
      return [];
    }
  }

  private async generateAISuggestions(event: CalendarEvent, context: any): Promise<{
    topics: string[];
    questions: string[];
    materials: string[];
  }> {
    try {
      // Use AI service to generate suggestions
      const aiRequest = {
        context: {
          event: {
            title: event.title,
            notes: event.notes,
            attendees: event.attendees,
          },
          previousMeetings: context.previousMeetings,
          relatedTasks: context.relatedTasks,
          relatedCode: context.relatedCode,
        },
        type: 'meeting' as const,
        priority: 'medium' as const,
        timestamp: Date.now(),
      };
      
      // This would call AIService in a real implementation
      // For now, generate basic suggestions
      const topics = this.generateBasicTopics(event);
      const questions = this.generateBasicQuestions(event, context);
      const materials = this.generateBasicMaterials(event, context);
      
      return { topics, questions, materials };
    } catch (error) {
      console.error('AI suggestions generation error:', error);
      return { topics: [], questions: [], materials: [] };
    }
  }

  private generateBasicTopics(event: CalendarEvent): string[] {
    const topics = [];
    const keywords = this.extractKeywords(event.title);
    
    topics.push(`Discussion on ${event.title}`);
    
    if (event.notes) {
      topics.push('Review agenda items');
    }
    
    if (keywords.includes('review')) {
      topics.push('Code review feedback');
      topics.push('Next steps and improvements');
    }
    
    if (keywords.includes('planning')) {
      topics.push('Sprint planning');
      topics.push('Resource allocation');
    }
    
    return topics;
  }

  private generateBasicQuestions(event: CalendarEvent, context: any): string[] {
    const questions = [];
    
    questions.push('What are the main objectives for this meeting?');
    
    if (context.relatedTasks.length > 0) {
      questions.push('What is the status of related tasks?');
    }
    
    if (context.previousMeetings.length > 0) {
      questions.push('What follow-ups from previous meetings need attention?');
    }
    
    if (event.attendees && event.attendees.length > 1) {
      questions.push('What updates does each team member have?');
    }
    
    return questions;
  }

  private generateBasicMaterials(event: CalendarEvent, context: any): string[] {
    const materials = [];
    
    if (context.relatedTasks.length > 0) {
      materials.push('Task board/project status');
    }
    
    if (context.relatedCode.length > 0) {
      materials.push('Code repositories and recent changes');
    }
    
    if (context.previousMeetings.length > 0) {
      materials.push('Previous meeting notes');
    }
    
    materials.push('Meeting agenda document');
    
    return materials;
  }

  private calculatePreparationScore(event: CalendarEvent, context: any): number {
    let score = 0;
    
    // Base score for having the meeting
    score += 20;
    
    // Agenda/notes
    if (event.notes && event.notes.length > 10) score += 20;
    
    // Related context
    if (context.previousMeetings.length > 0) score += 15;
    if (context.relatedTasks.length > 0) score += 15;
    if (context.relatedCode.length > 0) score += 10;
    
    // AI suggestions
    if (context.aiSuggestions.topics.length > 0) score += 10;
    if (context.aiSuggestions.questions.length > 0) score += 5;
    if (context.aiSuggestions.materials.length > 0) score += 5;
    
    return Math.min(100, score);
  }

  private calculateEventSimilarity(event1: CalendarEvent, event2: CalendarEvent): number {
    let similarity = 0;
    
    // Title similarity
    const titleSimilarity = this.calculateTextSimilarity(event1.title, event2.title);
    similarity += titleSimilarity * 0.4;
    
    // Attendee overlap
    const attendeeOverlap = this.calculateAttendeeOverlap(event1, event2);
    similarity += attendeeOverlap * 0.4;
    
    // Time proximity (meetings close in time are more similar)
    const timeDiff = Math.abs(event1.startDate.getTime() - event2.startDate.getTime());
    const daysDiff = timeDiff / (1000 * 60 * 60 * 24);
    const timeProximity = Math.max(0, 1 - daysDiff / 30); // Similar if within 30 days
    similarity += timeProximity * 0.2;
    
    return similarity;
  }

  private calculateTextSimilarity(text1: string, text2: string): number {
    const words1 = text1.toLowerCase().split(/\s+/);
    const words2 = text2.toLowerCase().split(/\s+/);
    
    const intersection = words1.filter(word => words2.includes(word));
    const union = [...new Set([...words1, ...words2])];
    
    return intersection.length / union.length;
  }

  private calculateAttendeeOverlap(event1: CalendarEvent, event2: CalendarEvent): number {
    if (!event1.attendees || !event2.attendees) return 0;
    
    const emails1 = event1.attendees.map(a => a.email);
    const emails2 = event2.attendees.map(a => a.email);
    
    const intersection = emails1.filter(email => emails2.includes(email));
    const union = [...new Set([...emails1, ...emails2])];
    
    return intersection.length / union.length;
  }

  private extractKeywords(text: string): string[] {
    const stopWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'];
    
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter(word => word.length > 2 && !stopWords.includes(word))
      .slice(0, 10);
  }

  private extractAgenda(event: CalendarEvent): string[] {
    const agenda = [];
    
    if (event.notes) {
      // Try to extract numbered items or bullet points
      const lines = event.notes.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.match(/^\d+\./) || trimmed.match(/^[-*]/) || trimmed.match(/^•/)) {
          agenda.push(trimmed);
        }
      }
    }
    
    return agenda;
  }

  async createCalendarEvent(eventData: Partial<CalendarEvent>): Promise<string> {
    if (!this.permissions.write) {
      throw new Error('Calendar write permission required');
    }
    
    try {
      const calendar = this.calendars.find(cal => cal.allowsModifications) || this.calendars[0];
      
      const eventId = await CalendarEvents.saveEvent(eventData.title || 'New Event', {
        calendarId: calendar.id,
        startDate: eventData.startDate?.toISOString() || new Date().toISOString(),
        endDate: eventData.endDate?.toISOString() || new Date(Date.now() + 3600000).toISOString(),
        location: eventData.location,
        notes: eventData.notes,
        url: eventData.url,
        allDay: eventData.isAllDay || false,
        alarms: eventData.alarms?.map(alarm => ({
          date: alarm.date.toISOString(),
          relativeOffset: alarm.relativeOffset,
        })),
      });
      
      // Refresh events to include the new one
      await this.loadEvents();
      
      return eventId;
    } catch (error) {
      console.error('Failed to create calendar event:', error);
      throw error;
    }
  }

  async deleteCalendarEvent(eventId: string): Promise<void> {
    if (!this.permissions.write) {
      throw new Error('Calendar write permission required');
    }
    
    try {
      await CalendarEvents.removeEvent(eventId);
      
      // Remove from local events
      this.events = this.events.filter(event => event.id !== eventId);
      
      // Remove preparation data
      this.preparations.delete(eventId);
      await this.saveMeetingPreparations();
    } catch (error) {
      console.error('Failed to delete calendar event:', error);
      throw error;
    }
  }

  startEventMonitoring(): void {
    if (this.monitoringInterval) return;
    
    this.monitoringInterval = BackgroundTimer.setInterval(async () => {
      try {
        await this.refreshUpcomingEvents();
        await this.checkForEventReminders();
      } catch (error) {
        console.error('Event monitoring error:', error);
      }
    }, 300000); // Check every 5 minutes
    
    console.log('Calendar event monitoring started');
  }

  stopEventMonitoring(): void {
    if (this.monitoringInterval) {
      BackgroundTimer.clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    
    console.log('Calendar event monitoring stopped');
  }

  private async checkForEventReminders(): Promise<void> {
    const upcomingEvents = this.getUpcomingEvents(2); // Next 2 hours
    
    for (const event of upcomingEvents) {
      const minutesToEvent = (event.startDate.getTime() - Date.now()) / (1000 * 60);
      
      // Send reminders at 30 minutes, 15 minutes, and 5 minutes
      const reminderTimes = [30, 15, 5];
      
      for (const reminderTime of reminderTimes) {
        if (Math.abs(minutesToEvent - reminderTime) < 2.5) { // Within 2.5 minutes
          await this.sendMeetingReminder(event, reminderTime);
        }
      }
    }
  }

  private async sendMeetingReminder(event: CalendarEvent, minutesBefore: number): Promise<void> {
    try {
      // Check if reminder already sent
      const reminderKey = `reminder_${event.id}_${minutesBefore}`;
      const alreadySent = await AsyncStorage.getItem(reminderKey);
      if (alreadySent) return;
      
      // Prepare meeting if it's a meeting
      let preparation: MeetingPreparation | null = null;
      if (this.isMeeting(event)) {
        preparation = await this.prepareMeeting(event);
      }
      
      // Send notification
      PushNotification.localNotification({
        title: `Meeting in ${minutesBefore} minutes`,
        message: event.title,
        userInfo: {
          type: 'meeting_reminder',
          data: {
            meetingId: event.id,
            preparation: preparation,
          },
        },
        actions: ['View Details', 'Join Meeting'],
      });
      
      // Mark reminder as sent
      await AsyncStorage.setItem(reminderKey, 'sent');
    } catch (error) {
      console.error('Meeting reminder error:', error);
    }
  }

  getCalendarInsights(days: number = 7): CalendarInsights {
    const startDate = new Date();
    const endDate = new Date();
    endDate.setDate(endDate.getDate() + days);
    
    const relevantEvents = this.events.filter(
      event => event.startDate >= startDate && event.startDate <= endDate
    );
    
    const meetingEvents = relevantEvents.filter(event => this.isMeeting(event));
    
    let meetingHours = 0;
    let overlapCount = 0;
    
    for (const event of meetingEvents) {
      const duration = (event.endDate.getTime() - event.startDate.getTime()) / (1000 * 60 * 60);
      meetingHours += duration;
      
      // Check for overlaps
      const overlaps = meetingEvents.filter(other => 
        other.id !== event.id &&
        other.startDate < event.endDate &&
        other.endDate > event.startDate
      );
      overlapCount += overlaps.length;
    }
    
    const totalHours = days * 8; // Assuming 8-hour work days
    const focusTime = totalHours - meetingHours;
    
    return {
      meetingHours,
      focusTime: Math.max(0, focusTime),
      overlapCount: overlapCount / 2, // Each overlap is counted twice
      travelTime: 0, // Could be enhanced with location analysis
      preparationTime: meetingEvents.length * 0.25, // 15 min prep per meeting
      efficiency: Math.max(0, Math.min(100, (focusTime / totalHours) * 100)),
    };
  }

  getMeetingPreparation(eventId: string): MeetingPreparation | undefined {
    return this.preparations.get(eventId);
  }

  getAllMeetingPreparations(): MeetingPreparation[] {
    return Array.from(this.preparations.values());
  }

  async exportCalendarData(): Promise<string> {
    try {
      const exportData = {
        events: this.events,
        preparations: Object.fromEntries(this.preparations),
        calendars: this.calendars,
        insights: this.getCalendarInsights(30),
        exportDate: new Date().toISOString(),
      };
      
      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      console.error('Calendar export error:', error);
      throw error;
    }
  }
}
