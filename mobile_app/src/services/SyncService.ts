/**
 * Sync Service - Advanced synchronization with conflict resolution
 * Handles bidirectional sync between mobile app and backend services
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import SQLite from 'react-native-sqlite-storage';
import DeviceInfo from 'react-native-device-info';

interface SyncItem {
  id: string;
  type: 'meeting' | 'task' | 'code' | 'profile' | 'calendar';
  action: 'create' | 'update' | 'delete';
  data: any;
  timestamp: number;
  synced: boolean;
  retryCount: number;
  lastSyncAttempt?: number;
  conflictData?: any;
}

interface SyncStatus {
  lastFullSync: number;
  lastQuickSync: number;
  pendingItems: number;
  failedItems: number;
  totalSynced: number;
  conflictsResolved: number;
}

export class SyncService {
  private baseUrl: string = 'http://localhost:8000';
  private db: SQLite.SQLiteDatabase | null = null;
  private isInitialized: boolean = false;
  private isSyncing: boolean = false;
  private syncQueue: SyncItem[] = [];
  private maxRetries: number = 3;
  private syncInterval: number = 300000; // 5 minutes
  private deviceId: string = '';

  async initialize(): Promise<void> {
    try {
      // Get device ID
      this.deviceId = await DeviceInfo.getUniqueId();

      // Initialize SQLite database
      await this.initializeDatabase();

      // Load sync queue from storage
      await this.loadSyncQueue();

      // Initialize sync status
      await this.initializeSyncStatus();

      this.isInitialized = true;
      console.log('Sync Service initialized');
    } catch (error) {
      console.error('Sync Service initialization error:', error);
      throw error;
    }
  }

  private async initializeDatabase(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: 'ai_sdlc_sync.db',
        location: 'default',
      });

      // Create sync tables
      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS sync_queue (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          action TEXT NOT NULL,
          data TEXT NOT NULL,
          timestamp INTEGER NOT NULL,
          synced INTEGER DEFAULT 0,
          retry_count INTEGER DEFAULT 0,
          last_sync_attempt INTEGER,
          conflict_data TEXT
        )
      `);

      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS sync_status (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        )
      `);

      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS conflict_resolution (
          id TEXT PRIMARY KEY,
          item_id TEXT NOT NULL,
          local_data TEXT NOT NULL,
          remote_data TEXT NOT NULL,
          resolution TEXT,
          resolved_at INTEGER,
          resolved_by TEXT
        )
      `);

      console.log('Sync database initialized');
    } catch (error) {
      console.error('Database initialization error:', error);
      throw error;
    }
  }

  private async loadSyncQueue(): Promise<void> {
    if (!this.db) return;

    try {
      const [results] = await this.db.executeSql(`
        SELECT * FROM sync_queue WHERE synced = 0 ORDER BY timestamp ASC
      `);

      this.syncQueue = [];
      for (let i = 0; i < results.rows.length; i++) {
        const row = results.rows.item(i);
        this.syncQueue.push({
          id: row.id,
          type: row.type,
          action: row.action,
          data: JSON.parse(row.data),
          timestamp: row.timestamp,
          synced: row.synced === 1,
          retryCount: row.retry_count,
          lastSyncAttempt: row.last_sync_attempt,
          conflictData: row.conflict_data ? JSON.parse(row.conflict_data) : undefined,
        });
      }

      console.log(`Loaded ${this.syncQueue.length} items from sync queue`);
    } catch (error) {
      console.error('Failed to load sync queue:', error);
    }
  }

  private async initializeSyncStatus(): Promise<void> {
    try {
      const defaultStatus: SyncStatus = {
        lastFullSync: 0,
        lastQuickSync: 0,
        pendingItems: 0,
        failedItems: 0,
        totalSynced: 0,
        conflictsResolved: 0,
      };

      const currentStatus = await this.getSyncStatus();
      if (!currentStatus.lastFullSync) {
        await this.updateSyncStatus(defaultStatus);
      }
    } catch (error) {
      console.error('Sync status initialization error:', error);
    }
  }

  async addToSyncQueue(item: Omit<SyncItem, 'id' | 'synced' | 'retryCount'>): Promise<void> {
    if (!this.db) return;

    const syncItem: SyncItem = {
      ...item,
      id: `${item.type}_${item.action}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      synced: false,
      retryCount: 0,
    };

    try {
      // Add to database
      await this.db.executeSql(`
        INSERT INTO sync_queue (id, type, action, data, timestamp, synced, retry_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `, [
        syncItem.id,
        syncItem.type,
        syncItem.action,
        JSON.stringify(syncItem.data),
        syncItem.timestamp,
        0,
        0,
      ]);

      // Add to memory queue
      this.syncQueue.push(syncItem);

      console.log(`Added item to sync queue: ${syncItem.type}/${syncItem.action}`);
    } catch (error) {
      console.error('Failed to add item to sync queue:', error);
    }
  }

  async performFullSync(): Promise<void> {
    if (this.isSyncing) {
      console.log('Sync already in progress');
      return;
    }

    this.isSyncing = true;
    console.log('Starting full sync...');

    try {
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) {
        throw new Error('No internet connection');
      }

      // Sync all data types
      await Promise.all([
        this.syncUserProfile(),
        this.syncMeetings(),
        this.syncTasks(),
        this.syncCodeData(),
        this.syncCalendarEvents(),
      ]);

      // Process sync queue
      await this.processSyncQueue();

      // Update sync status
      const status = await this.getSyncStatus();
      status.lastFullSync = Date.now();
      status.pendingItems = this.syncQueue.filter(item => !item.synced).length;
      await this.updateSyncStatus(status);

      console.log('Full sync completed');
    } catch (error) {
      console.error('Full sync error:', error);
      throw error;
    } finally {
      this.isSyncing = false;
    }
  }

  async performQuickSync(): Promise<void> {
    if (this.isSyncing) return;

    this.isSyncing = true;
    console.log('Starting quick sync...');

    try {
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) {
        throw new Error('No internet connection');
      }

      // Process only recent changes
      const recentItems = this.syncQueue.filter(
        item => !item.synced && Date.now() - item.timestamp < 3600000 // Last hour
      );

      for (const item of recentItems) {
        await this.syncItem(item);
      }

      // Update sync status
      const status = await this.getSyncStatus();
      status.lastQuickSync = Date.now();
      status.pendingItems = this.syncQueue.filter(item => !item.synced).length;
      await this.updateSyncStatus(status);

      console.log('Quick sync completed');
    } catch (error) {
      console.error('Quick sync error:', error);
    } finally {
      this.isSyncing = false;
    }
  }

  async performBackgroundSync(): Promise<void> {
    if (this.isSyncing) return;

    console.log('Starting background sync...');
    
    try {
      // Lightweight sync for background processing
      const highPriorityItems = this.syncQueue.filter(
        item => !item.synced && item.retryCount < this.maxRetries
      ).slice(0, 10); // Limit to 10 items

      for (const item of highPriorityItems) {
        await this.syncItem(item);
      }
    } catch (error) {
      console.error('Background sync error:', error);
    }
  }

  async syncOfflineChanges(): Promise<void> {
    console.log('Syncing offline changes...');
    
    try {
      // Process all offline changes
      await this.processSyncQueue();
      
      // Pull latest changes from server
      await this.pullLatestChanges();
      
    } catch (error) {
      console.error('Offline changes sync error:', error);
    }
  }

  private async processSyncQueue(): Promise<void> {
    const unsynced = this.syncQueue.filter(item => !item.synced);
    
    console.log(`Processing ${unsynced.length} unsynced items`);
    
    for (const item of unsynced) {
      if (item.retryCount >= this.maxRetries) {
        console.warn(`Skipping item after ${this.maxRetries} retries:`, item.id);
        continue;
      }
      
      await this.syncItem(item);
    }
  }

  private async syncItem(item: SyncItem): Promise<void> {
    try {
      const endpoint = this.getEndpointForItem(item);
      const method = this.getMethodForAction(item.action);
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': this.deviceId,
          'X-Sync-Timestamp': item.timestamp.toString(),
        },
        body: method !== 'GET' ? JSON.stringify({
          ...item.data,
          syncId: item.id,
          action: item.action,
        }) : undefined,
      });

      if (response.ok) {
        const result = await response.json();
        
        // Check for conflicts
        if (result.conflict) {
          await this.handleConflict(item, result.conflict);
        } else {
          await this.markItemSynced(item);
        }
      } else if (response.status === 409) {
        // Conflict detected
        const conflictData = await response.json();
        await this.handleConflict(item, conflictData);
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error(`Failed to sync item ${item.id}:`, error);
      await this.handleSyncFailure(item, error);
    }
  }

  private async handleConflict(item: SyncItem, conflictData: any): Promise<void> {
    console.log(`Conflict detected for item ${item.id}`);
    
    if (!this.db) return;

    try {
      // Store conflict for resolution
      await this.db.executeSql(`
        INSERT OR REPLACE INTO conflict_resolution (id, item_id, local_data, remote_data)
        VALUES (?, ?, ?, ?)
      `, [
        `conflict_${item.id}`,
        item.id,
        JSON.stringify(item.data),
        JSON.stringify(conflictData),
      ]);

      // Apply conflict resolution strategy
      const resolution = await this.resolveConflict(item, conflictData);
      
      if (resolution) {
        // Update item with resolved data
        item.data = resolution.data;
        item.conflictData = conflictData;
        
        // Retry sync with resolved data
        await this.syncItem(item);
        
        // Mark conflict as resolved
        await this.db.executeSql(`
          UPDATE conflict_resolution 
          SET resolution = ?, resolved_at = ?, resolved_by = ?
          WHERE item_id = ?
        `, [
          JSON.stringify(resolution),
          Date.now(),
          'auto',
          item.id,
        ]);
      }
    } catch (error) {
      console.error('Conflict handling error:', error);
    }
  }

  private async resolveConflict(localItem: SyncItem, remoteData: any): Promise<any> {
    // Implement conflict resolution strategies
    const strategy = await this.getConflictResolutionStrategy(localItem.type);
    
    switch (strategy) {
      case 'latest_wins':
        return localItem.timestamp > remoteData.timestamp ? localItem : { data: remoteData };
      
      case 'merge':
        return { data: this.mergeData(localItem.data, remoteData) };
      
      case 'remote_wins':
        return { data: remoteData };
      
      case 'local_wins':
        return localItem;
      
      default:
        // Default to latest wins
        return localItem.timestamp > remoteData.timestamp ? localItem : { data: remoteData };
    }
  }

  private mergeData(localData: any, remoteData: any): any {
    // Simple merge strategy - can be enhanced per data type
    return {
      ...remoteData,
      ...localData,
      lastModified: Math.max(localData.lastModified || 0, remoteData.lastModified || 0),
    };
  }

  private async getConflictResolutionStrategy(type: string): Promise<string> {
    try {
      const strategy = await AsyncStorage.getItem(`conflict_strategy_${type}`);
      return strategy || 'latest_wins';
    } catch {
      return 'latest_wins';
    }
  }

  private async markItemSynced(item: SyncItem): Promise<void> {
    if (!this.db) return;

    try {
      await this.db.executeSql(`
        UPDATE sync_queue SET synced = 1 WHERE id = ?
      `, [item.id]);

      // Update memory
      const index = this.syncQueue.findIndex(q => q.id === item.id);
      if (index !== -1) {
        this.syncQueue[index].synced = true;
      }

      // Update sync status
      const status = await this.getSyncStatus();
      status.totalSynced++;
      await this.updateSyncStatus(status);

      console.log(`Item synced: ${item.id}`);
    } catch (error) {
      console.error('Failed to mark item as synced:', error);
    }
  }

  private async handleSyncFailure(item: SyncItem, error: any): Promise<void> {
    if (!this.db) return;

    try {
      const retryCount = item.retryCount + 1;
      
      await this.db.executeSql(`
        UPDATE sync_queue 
        SET retry_count = ?, last_sync_attempt = ?
        WHERE id = ?
      `, [retryCount, Date.now(), item.id]);

      // Update memory
      const index = this.syncQueue.findIndex(q => q.id === item.id);
      if (index !== -1) {
        this.syncQueue[index].retryCount = retryCount;
        this.syncQueue[index].lastSyncAttempt = Date.now();
      }

      // Update failed items count
      if (retryCount >= this.maxRetries) {
        const status = await this.getSyncStatus();
        status.failedItems++;
        await this.updateSyncStatus(status);
      }
    } catch (dbError) {
      console.error('Failed to handle sync failure:', dbError);
    }
  }

  // Specific sync methods
  async syncUserProfile(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/profile`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const profile = await response.json();
        await AsyncStorage.setItem('user_profile', JSON.stringify(profile));
      }
    } catch (error) {
      console.error('Profile sync error:', error);
    }
  }

  async syncMeetings(): Promise<void> {
    try {
      const lastSync = (await this.getSyncStatus()).lastFullSync;
      const response = await fetch(`${this.baseUrl}/api/meetings?since=${lastSync}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const meetings = await response.json();
        await AsyncStorage.setItem('meetings', JSON.stringify(meetings));
      }
    } catch (error) {
      console.error('Meetings sync error:', error);
    }
  }

  async syncTasks(): Promise<void> {
    try {
      const lastSync = (await this.getSyncStatus()).lastFullSync;
      const response = await fetch(`${this.baseUrl}/api/tasks?since=${lastSync}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const tasks = await response.json();
        await AsyncStorage.setItem('tasks', JSON.stringify(tasks));
      }
    } catch (error) {
      console.error('Tasks sync error:', error);
    }
  }

  async syncCodeData(): Promise<void> {
    try {
      const lastSync = (await this.getSyncStatus()).lastFullSync;
      const response = await fetch(`${this.baseUrl}/api/code?since=${lastSync}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const codeData = await response.json();
        await AsyncStorage.setItem('code_data', JSON.stringify(codeData));
      }
    } catch (error) {
      console.error('Code data sync error:', error);
    }
  }

  async syncTaskData(taskId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tasks/${taskId}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const task = await response.json();
        // Update local task data
        const tasks = JSON.parse(await AsyncStorage.getItem('tasks') || '[]');
        const index = tasks.findIndex((t: any) => t.id === taskId);
        if (index !== -1) {
          tasks[index] = task;
          await AsyncStorage.setItem('tasks', JSON.stringify(tasks));
        }
      }
    } catch (error) {
      console.error('Task data sync error:', error);
    }
  }

  async syncCodeData(reviewId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/code/reviews/${reviewId}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const review = await response.json();
        // Update local review data
        const reviews = JSON.parse(await AsyncStorage.getItem('code_reviews') || '[]');
        const index = reviews.findIndex((r: any) => r.id === reviewId);
        if (index !== -1) {
          reviews[index] = review;
          await AsyncStorage.setItem('code_reviews', JSON.stringify(reviews));
        }
      }
    } catch (error) {
      console.error('Code review sync error:', error);
    }
  }

  async syncCalendarEvents(): Promise<void> {
    // This will be handled by CalendarService
    console.log('Calendar events sync delegated to CalendarService');
  }

  private async pullLatestChanges(): Promise<void> {
    try {
      const lastSync = (await this.getSyncStatus()).lastFullSync;
      const response = await fetch(`${this.baseUrl}/api/sync/changes?since=${lastSync}`, {
        headers: { 'X-Device-ID': this.deviceId },
      });
      
      if (response.ok) {
        const changes = await response.json();
        await this.applyRemoteChanges(changes);
      }
    } catch (error) {
      console.error('Pull latest changes error:', error);
    }
  }

  private async applyRemoteChanges(changes: any[]): Promise<void> {
    for (const change of changes) {
      try {
        await this.applyRemoteChange(change);
      } catch (error) {
        console.error('Failed to apply remote change:', error);
      }
    }
  }

  private async applyRemoteChange(change: any): Promise<void> {
    const { type, action, data } = change;
    
    switch (type) {
      case 'meeting':
        await this.applyMeetingChange(action, data);
        break;
      case 'task':
        await this.applyTaskChange(action, data);
        break;
      case 'code':
        await this.applyCodeChange(action, data);
        break;
      default:
        console.warn('Unknown change type:', type);
    }
  }

  private async applyMeetingChange(action: string, data: any): Promise<void> {
    const meetings = JSON.parse(await AsyncStorage.getItem('meetings') || '[]');
    
    switch (action) {
      case 'create':
        meetings.push(data);
        break;
      case 'update':
        const updateIndex = meetings.findIndex((m: any) => m.id === data.id);
        if (updateIndex !== -1) {
          meetings[updateIndex] = data;
        }
        break;
      case 'delete':
        const deleteIndex = meetings.findIndex((m: any) => m.id === data.id);
        if (deleteIndex !== -1) {
          meetings.splice(deleteIndex, 1);
        }
        break;
    }
    
    await AsyncStorage.setItem('meetings', JSON.stringify(meetings));
  }

  private async applyTaskChange(action: string, data: any): Promise<void> {
    const tasks = JSON.parse(await AsyncStorage.getItem('tasks') || '[]');
    
    switch (action) {
      case 'create':
        tasks.push(data);
        break;
      case 'update':
        const updateIndex = tasks.findIndex((t: any) => t.id === data.id);
        if (updateIndex !== -1) {
          tasks[updateIndex] = data;
        }
        break;
      case 'delete':
        const deleteIndex = tasks.findIndex((t: any) => t.id === data.id);
        if (deleteIndex !== -1) {
          tasks.splice(deleteIndex, 1);
        }
        break;
    }
    
    await AsyncStorage.setItem('tasks', JSON.stringify(tasks));
  }

  private async applyCodeChange(action: string, data: any): Promise<void> {
    const codeData = JSON.parse(await AsyncStorage.getItem('code_data') || '[]');
    
    switch (action) {
      case 'create':
        codeData.push(data);
        break;
      case 'update':
        const updateIndex = codeData.findIndex((c: any) => c.id === data.id);
        if (updateIndex !== -1) {
          codeData[updateIndex] = data;
        }
        break;
      case 'delete':
        const deleteIndex = codeData.findIndex((c: any) => c.id === data.id);
        if (deleteIndex !== -1) {
          codeData.splice(deleteIndex, 1);
        }
        break;
    }
    
    await AsyncStorage.setItem('code_data', JSON.stringify(codeData));
  }

  // Utility methods
  private getEndpointForItem(item: SyncItem): string {
    const endpoints = {
      meeting: '/api/meetings',
      task: '/api/tasks',
      code: '/api/code',
      profile: '/api/profile',
      calendar: '/api/calendar',
    };
    
    return endpoints[item.type] || '/api/sync';
  }

  private getMethodForAction(action: string): string {
    const methods = {
      create: 'POST',
      update: 'PUT',
      delete: 'DELETE',
    };
    
    return methods[action] || 'POST';
  }

  async getSyncStatus(): Promise<SyncStatus> {
    if (!this.db) {
      return {
        lastFullSync: 0,
        lastQuickSync: 0,
        pendingItems: 0,
        failedItems: 0,
        totalSynced: 0,
        conflictsResolved: 0,
      };
    }

    try {
      const [results] = await this.db.executeSql(`
        SELECT key, value FROM sync_status
      `);
      
      const status: any = {};
      for (let i = 0; i < results.rows.length; i++) {
        const row = results.rows.item(i);
        status[row.key] = JSON.parse(row.value);
      }
      
      return status;
    } catch (error) {
      console.error('Failed to get sync status:', error);
      return {
        lastFullSync: 0,
        lastQuickSync: 0,
        pendingItems: 0,
        failedItems: 0,
        totalSynced: 0,
        conflictsResolved: 0,
      };
    }
  }

  private async updateSyncStatus(status: SyncStatus): Promise<void> {
    if (!this.db) return;

    try {
      for (const [key, value] of Object.entries(status)) {
        await this.db.executeSql(`
          INSERT OR REPLACE INTO sync_status (key, value, updated_at)
          VALUES (?, ?, ?)
        `, [key, JSON.stringify(value), Date.now()]);
      }
    } catch (error) {
      console.error('Failed to update sync status:', error);
    }
  }

  getPendingItemsCount(): number {
    return this.syncQueue.filter(item => !item.synced).length;
  }

  getFailedItemsCount(): number {
    return this.syncQueue.filter(item => item.retryCount >= this.maxRetries).length;
  }

  async clearSyncQueue(): Promise<void> {
    if (!this.db) return;

    try {
      await this.db.executeSql('DELETE FROM sync_queue WHERE synced = 1');
      this.syncQueue = this.syncQueue.filter(item => !item.synced);
      console.log('Sync queue cleared');
    } catch (error) {
      console.error('Failed to clear sync queue:', error);
    }
  }

  async resetSync(): Promise<void> {
    if (!this.db) return;

    try {
      await this.db.executeSql('DELETE FROM sync_queue');
      await this.db.executeSql('DELETE FROM sync_status');
      await this.db.executeSql('DELETE FROM conflict_resolution');
      
      this.syncQueue = [];
      await this.initializeSyncStatus();
      
      console.log('Sync data reset');
    } catch (error) {
      console.error('Failed to reset sync:', error);
    }
  }
}
