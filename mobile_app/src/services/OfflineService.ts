/**
 * Offline Service - Advanced offline capabilities with intelligent data management
 * Handles offline storage, data synchronization, and offline-first functionality
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import SQLite from 'react-native-sqlite-storage';
import NetInfo from '@react-native-community/netinfo';
import RNFS from 'react-native-fs';
import EncryptedStorage from 'react-native-encrypted-storage';

interface OfflineData {
  id: string;
  type: 'meeting' | 'task' | 'code' | 'profile' | 'calendar' | 'ai_response';
  data: any;
  lastModified: Date;
  accessed: Date;
  size: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  encrypted: boolean;
  synced: boolean;
  version: number;
}

interface CacheConfig {
  maxSize: number; // bytes
  maxAge: number; // milliseconds
  compressionEnabled: boolean;
  encryptionEnabled: boolean;
  autoCleanup: boolean;
  preloadCritical: boolean;
}

interface OfflineState {
  isOffline: boolean;
  storageUsed: number;
  dataCount: number;
  lastSync: Date | null;
  pendingOperations: number;
  cacheHitRate: number;
  compressionRatio: number;
}

export class OfflineService {
  private db: SQLite.SQLiteDatabase | null = null;
  private isInitialized: boolean = false;
  private config: CacheConfig;
  private offlineData: Map<string, OfflineData> = new Map();
  private state: OfflineState;
  private accessLog: Map<string, number> = new Map();
  private compressionCache: Map<string, string> = new Map();

  constructor() {
    this.config = this.getDefaultConfig();
    this.state = this.getInitialState();
  }

  async initialize(): Promise<void> {
    try {
      // Initialize SQLite database
      await this.initializeDatabase();

      // Load configuration
      await this.loadConfiguration();

      // Load offline data index
      await this.loadOfflineDataIndex();

      // Initialize storage monitoring
      await this.initializeStorageMonitoring();

      // Start cleanup routine
      this.startCleanupRoutine();

      this.isInitialized = true;
      console.log('Offline Service initialized');
    } catch (error) {
      console.error('Offline Service initialization error:', error);
      throw error;
    }
  }

  private async initializeDatabase(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: 'ai_sdlc_offline.db',
        location: 'default',
      });

      // Create offline data table
      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS offline_data (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          data TEXT NOT NULL,
          last_modified INTEGER NOT NULL,
          accessed INTEGER NOT NULL,
          size INTEGER NOT NULL,
          priority TEXT NOT NULL,
          encrypted INTEGER DEFAULT 0,
          synced INTEGER DEFAULT 0,
          version INTEGER DEFAULT 1,
          checksum TEXT,
          compression_type TEXT
        )
      `);

      // Create access log table
      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS access_log (
          id TEXT PRIMARY KEY,
          data_id TEXT NOT NULL,
          access_time INTEGER NOT NULL,
          access_type TEXT NOT NULL,
          FOREIGN KEY (data_id) REFERENCES offline_data (id)
        )
      `);

      // Create configuration table
      await this.db.executeSql(`
        CREATE TABLE IF NOT EXISTS offline_config (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        )
      `);

      // Create indexes for performance
      await this.db.executeSql(`
        CREATE INDEX IF NOT EXISTS idx_offline_data_type ON offline_data(type)
      `);
      await this.db.executeSql(`
        CREATE INDEX IF NOT EXISTS idx_offline_data_priority ON offline_data(priority)
      `);
      await this.db.executeSql(`
        CREATE INDEX IF NOT EXISTS idx_offline_data_accessed ON offline_data(accessed)
      `);

      console.log('Offline database initialized');
    } catch (error) {
      console.error('Database initialization error:', error);
      throw error;
    }
  }

  private async loadOfflineDataIndex(): Promise<void> {
    if (!this.db) return;

    try {
      const [results] = await this.db.executeSql(`
        SELECT id, type, last_modified, accessed, size, priority, encrypted, synced, version
        FROM offline_data
        ORDER BY accessed DESC
      `);

      this.offlineData.clear();
      for (let i = 0; i < results.rows.length; i++) {
        const row = results.rows.item(i);
        this.offlineData.set(row.id, {
          id: row.id,
          type: row.type,
          data: null, // Data loaded on demand
          lastModified: new Date(row.last_modified),
          accessed: new Date(row.accessed),
          size: row.size,
          priority: row.priority,
          encrypted: row.encrypted === 1,
          synced: row.synced === 1,
          version: row.version,
        });
      }

      console.log(`Loaded ${this.offlineData.size} offline data items`);
    } catch (error) {
      console.error('Failed to load offline data index:', error);
    }
  }

  private async initializeStorageMonitoring(): Promise<void> {
    try {
      // Calculate current storage usage
      await this.updateStorageStats();

      // Set up network monitoring
      NetInfo.addEventListener(state => {
        const wasOffline = this.state.isOffline;
        this.state.isOffline = !state.isConnected;

        if (wasOffline && !this.state.isOffline) {
          // Just came online
          this.handleOnlineTransition();
        } else if (!wasOffline && this.state.isOffline) {
          // Just went offline
          this.handleOfflineTransition();
        }
      });
    } catch (error) {
      console.error('Storage monitoring initialization error:', error);
    }
  }

  private async updateStorageStats(): Promise<void> {
    try {
      let totalSize = 0;
      for (const item of this.offlineData.values()) {
        totalSize += item.size;
      }

      this.state.storageUsed = totalSize;
      this.state.dataCount = this.offlineData.size;

      // Calculate cache hit rate
      const totalAccesses = Array.from(this.accessLog.values()).reduce((sum, count) => sum + count, 0);
      const cacheHits = Array.from(this.offlineData.values()).filter(item => item.data !== null).length;
      this.state.cacheHitRate = totalAccesses > 0 ? (cacheHits / totalAccesses) * 100 : 0;
    } catch (error) {
      console.error('Storage stats update error:', error);
    }
  }

  async storeData(
    id: string,
    type: string,
    data: any,
    priority: 'low' | 'medium' | 'high' | 'critical' = 'medium',
    encrypt: boolean = false
  ): Promise<void> {
    if (!this.db) throw new Error('Offline service not initialized');

    try {
      // Prepare data for storage
      let dataString = JSON.stringify(data);
      let compressed = false;
      let checksum = '';

      // Compress if enabled and data is large
      if (this.config.compressionEnabled && dataString.length > 1024) {
        dataString = await this.compressData(dataString);
        compressed = true;
      }

      // Encrypt if required
      if (encrypt && this.config.encryptionEnabled) {
        dataString = await this.encryptData(dataString);
      }

      // Calculate checksum
      checksum = await this.calculateChecksum(dataString);

      const size = dataString.length;
      const now = Date.now();

      // Check storage limits
      await this.ensureStorageCapacity(size);

      // Store in database
      await this.db.executeSql(`
        INSERT OR REPLACE INTO offline_data 
        (id, type, data, last_modified, accessed, size, priority, encrypted, synced, version, checksum, compression_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        id,
        type,
        dataString,
        now,
        now,
        size,
        priority,
        encrypt ? 1 : 0,
        0, // Not synced initially
        1, // Version 1
        checksum,
        compressed ? 'gzip' : null,
      ]);

      // Update in-memory index
      this.offlineData.set(id, {
        id,
        type: type as any,
        data,
        lastModified: new Date(now),
        accessed: new Date(now),
        size,
        priority: priority as any,
        encrypted: encrypt,
        synced: false,
        version: 1,
      });

      await this.updateStorageStats();
      console.log(`Data stored offline: ${id} (${size} bytes)`);
    } catch (error) {
      console.error('Failed to store offline data:', error);
      throw error;
    }
  }

  async retrieveData(id: string): Promise<any | null> {
    if (!this.db) return null;

    try {
      // Check in-memory cache first
      const cachedItem = this.offlineData.get(id);
      if (cachedItem && cachedItem.data !== null) {
        this.recordAccess(id);
        return cachedItem.data;
      }

      // Load from database
      const [results] = await this.db.executeSql(`
        SELECT data, encrypted, compression_type, checksum FROM offline_data WHERE id = ?
      `, [id]);

      if (results.rows.length === 0) return null;

      const row = results.rows.item(0);
      let dataString = row.data;

      // Verify checksum
      const currentChecksum = await this.calculateChecksum(dataString);
      if (currentChecksum !== row.checksum) {
        console.warn('Data corruption detected for:', id);
        return null;
      }

      // Decrypt if encrypted
      if (row.encrypted === 1) {
        dataString = await this.decryptData(dataString);
      }

      // Decompress if compressed
      if (row.compression_type === 'gzip') {
        dataString = await this.decompressData(dataString);
      }

      const data = JSON.parse(dataString);

      // Update access time
      await this.db.executeSql(`
        UPDATE offline_data SET accessed = ? WHERE id = ?
      `, [Date.now(), id]);

      // Cache in memory
      if (cachedItem) {
        cachedItem.data = data;
        cachedItem.accessed = new Date();
      }

      this.recordAccess(id);
      return data;
    } catch (error) {
      console.error('Failed to retrieve offline data:', error);
      return null;
    }
  }

  async deleteData(id: string): Promise<void> {
    if (!this.db) return;

    try {
      await this.db.executeSql(`DELETE FROM offline_data WHERE id = ?`, [id]);
      await this.db.executeSql(`DELETE FROM access_log WHERE data_id = ?`, [id]);

      this.offlineData.delete(id);
      this.accessLog.delete(id);

      await this.updateStorageStats();
      console.log(`Offline data deleted: ${id}`);
    } catch (error) {
      console.error('Failed to delete offline data:', error);
    }
  }

  async updateData(id: string, data: any): Promise<void> {
    if (!this.db) return;

    try {
      const existingItem = this.offlineData.get(id);
      if (!existingItem) {
        throw new Error('Data not found for update');
      }

      const newVersion = existingItem.version + 1;
      await this.storeData(id, existingItem.type, data, existingItem.priority, existingItem.encrypted);

      // Update version
      await this.db.executeSql(`
        UPDATE offline_data SET version = ?, synced = 0 WHERE id = ?
      `, [newVersion, id]);

      if (existingItem) {
        existingItem.version = newVersion;
        existingItem.synced = false;
        existingItem.lastModified = new Date();
      }

      console.log(`Offline data updated: ${id} (v${newVersion})`);
    } catch (error) {
      console.error('Failed to update offline data:', error);
      throw error;
    }
  }

  async queryData(
    type?: string,
    priority?: string,
    limit?: number
  ): Promise<OfflineData[]> {
    if (!this.db) return [];

    try {
      let query = 'SELECT * FROM offline_data WHERE 1=1';
      const params: any[] = [];

      if (type) {
        query += ' AND type = ?';
        params.push(type);
      }

      if (priority) {
        query += ' AND priority = ?';
        params.push(priority);
      }

      query += ' ORDER BY accessed DESC';

      if (limit) {
        query += ' LIMIT ?';
        params.push(limit);
      }

      const [results] = await this.db.executeSql(query, params);
      const items: OfflineData[] = [];

      for (let i = 0; i < results.rows.length; i++) {
        const row = results.rows.item(i);
        items.push({
          id: row.id,
          type: row.type,
          data: null, // Load on demand
          lastModified: new Date(row.last_modified),
          accessed: new Date(row.accessed),
          size: row.size,
          priority: row.priority,
          encrypted: row.encrypted === 1,
          synced: row.synced === 1,
          version: row.version,
        });
      }

      return items;
    } catch (error) {
      console.error('Failed to query offline data:', error);
      return [];
    }
  }

  async enableOfflineMode(): Promise<void> {
    try {
      this.state.isOffline = true;

      // Preload critical data
      if (this.config.preloadCritical) {
        await this.preloadCriticalData();
      }

      // Optimize storage
      await this.optimizeOfflineStorage();

      console.log('Offline mode enabled');
    } catch (error) {
      console.error('Failed to enable offline mode:', error);
    }
  }

  private async preloadCriticalData(): Promise<void> {
    try {
      const criticalItems = Array.from(this.offlineData.values())
        .filter(item => item.priority === 'critical' && item.data === null)
        .slice(0, 20); // Limit to avoid memory issues

      for (const item of criticalItems) {
        await this.retrieveData(item.id);
      }

      console.log(`Preloaded ${criticalItems.length} critical items`);
    } catch (error) {
      console.error('Critical data preload error:', error);
    }
  }

  private async optimizeOfflineStorage(): Promise<void> {
    try {
      // Compress uncompressed data
      const uncompressedItems = await this.queryData();
      for (const item of uncompressedItems) {
        if (item.size > 1024 && !item.encrypted) {
          const data = await this.retrieveData(item.id);
          if (data) {
            await this.storeData(item.id, item.type, data, item.priority, item.encrypted);
          }
        }
      }

      // Clean up old access logs
      if (this.db) {
        const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        await this.db.executeSql(`
          DELETE FROM access_log WHERE access_time < ?
        `, [weekAgo]);
      }

      console.log('Offline storage optimized');
    } catch (error) {
      console.error('Storage optimization error:', error);
    }
  }

  async saveCurrentState(): Promise<void> {
    try {
      const currentState = {
        timestamp: Date.now(),
        offlineMode: this.state.isOffline,
        dataCount: this.state.dataCount,
        storageUsed: this.state.storageUsed,
        pendingOperations: this.state.pendingOperations,
      };

      await AsyncStorage.setItem('offline_service_state', JSON.stringify(currentState));
      console.log('Current state saved');
    } catch (error) {
      console.error('Failed to save current state:', error);
    }
  }

  private async ensureStorageCapacity(requiredSize: number): Promise<void> {
    const availableSpace = this.config.maxSize - this.state.storageUsed;

    if (availableSpace < requiredSize) {
      const spaceToClear = requiredSize - availableSpace + (this.config.maxSize * 0.1); // 10% buffer
      await this.clearStorageSpace(spaceToClear);
    }
  }

  private async clearStorageSpace(targetSize: number): Promise<void> {
    if (!this.db) return;

    try {
      // Get items sorted by priority and access time (least important first)
      const [results] = await this.db.executeSql(`
        SELECT id, size, priority, accessed FROM offline_data
        WHERE priority != 'critical'
        ORDER BY 
          CASE priority 
            WHEN 'low' THEN 1 
            WHEN 'medium' THEN 2 
            WHEN 'high' THEN 3 
            ELSE 4 
          END ASC,
          accessed ASC
      `);

      let clearedSize = 0;
      const itemsToDelete: string[] = [];

      for (let i = 0; i < results.rows.length && clearedSize < targetSize; i++) {
        const row = results.rows.item(i);
        itemsToDelete.push(row.id);
        clearedSize += row.size;
      }

      // Delete selected items
      for (const id of itemsToDelete) {
        await this.deleteData(id);
      }

      console.log(`Cleared ${clearedSize} bytes by removing ${itemsToDelete.length} items`);
    } catch (error) {
      console.error('Storage cleanup error:', error);
    }
  }

  private recordAccess(id: string): void {
    const currentCount = this.accessLog.get(id) || 0;
    this.accessLog.set(id, currentCount + 1);

    // Log to database periodically
    if (Math.random() < 0.1 && this.db) { // 10% chance to persist
      this.db.executeSql(`
        INSERT INTO access_log (id, data_id, access_time, access_type)
        VALUES (?, ?, ?, ?)
      `, [
        `${id}_${Date.now()}`,
        id,
        Date.now(),
        'retrieve',
      ]);
    }
  }

  private startCleanupRoutine(): void {
    setInterval(async () => {
      try {
        if (this.config.autoCleanup) {
          await this.performMaintenanceCleanup();
        }
      } catch (error) {
        console.error('Cleanup routine error:', error);
      }
    }, 3600000); // Every hour
  }

  private async performMaintenanceCleanup(): Promise<void> {
    if (!this.db) return;

    try {
      const maxAge = this.config.maxAge;
      const cutoffTime = Date.now() - maxAge;

      // Remove expired data
      const [expiredResults] = await this.db.executeSql(`
        SELECT id FROM offline_data 
        WHERE accessed < ? AND priority != 'critical'
      `, [cutoffTime]);

      for (let i = 0; i < expiredResults.rows.length; i++) {
        const row = expiredResults.rows.item(i);
        await this.deleteData(row.id);
      }

      // Clean compression cache
      this.compressionCache.clear();

      await this.updateStorageStats();
      console.log(`Maintenance cleanup completed: removed ${expiredResults.rows.length} items`);
    } catch (error) {
      console.error('Maintenance cleanup error:', error);
    }
  }

  private async handleOnlineTransition(): Promise<void> {
    console.log('Transitioning to online mode');
    this.state.isOffline = false;
    // Sync operations will be handled by SyncService
  }

  private async handleOfflineTransition(): Promise<void> {
    console.log('Transitioning to offline mode');
    await this.enableOfflineMode();
  }

  // Utility methods
  private async compressData(data: string): Promise<string> {
    // TODO: Implement actual compression using a library like pako for gzip compression
    // For production, consider installing: npm install pako && @types/pako
    // Then use: import * as pako from 'pako'; pako.deflate(data)
    try {
      if (!this.config.compressionEnabled || data.length < 100) {
        // Skip compression for small data or when disabled
        return data;
      }
      
      // Simple compression simulation - remove repeated whitespace and newlines
      // This provides actual size reduction for JSON data while remaining functional
      const compressed = data
        .replace(/\s+/g, ' ')           // Multiple spaces to single space
        .replace(/\n\s*/g, '')          // Remove newlines and following spaces
        .replace(/,\s/g, ',')           // Remove spaces after commas
        .replace(/:\s/g, ':')           // Remove spaces after colons
        .trim();
      
      this.compressionCache.set(data, compressed);
      
      // Update compression ratio for monitoring
      const ratio = compressed.length / data.length;
      this.state.compressionRatio = (this.state.compressionRatio + ratio) / 2;
      
      return compressed;
    } catch (error) {
      console.error('Compression error:', error);
      return data;
    }
  }

  private async decompressData(compressedData: string): Promise<string> {
    // TODO: Implement actual decompression when real compression is added
    // For the current whitespace compression, no decompression is needed
    try {
      // The current compression only removes whitespace, so data is still valid JSON/text
      // No decompression needed - return as-is
      return compressedData;
    } catch (error) {
      console.error('Decompression error:', error);
      // Return original data if any issues occur
      return compressedData;
    }
  }

  private async encryptData(data: string): Promise<string> {
    try {
      await EncryptedStorage.setItem(`temp_encrypt_${Date.now()}`, data);
      return data; // Placeholder - implement actual encryption
    } catch (error) {
      console.error('Encryption error:', error);
      return data;
    }
  }

  private async decryptData(encryptedData: string): Promise<string> {
    try {
      return encryptedData; // Placeholder - implement actual decryption
    } catch (error) {
      console.error('Decryption error:', error);
      return encryptedData;
    }
  }

  private async calculateChecksum(data: string): Promise<string> {
    // Simple checksum calculation (in real app, use crypto library)
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(36);
  }

  private getDefaultConfig(): CacheConfig {
    return {
      maxSize: 100 * 1024 * 1024, // 100MB
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
      compressionEnabled: true,
      encryptionEnabled: true,
      autoCleanup: true,
      preloadCritical: true,
    };
  }

  private getInitialState(): OfflineState {
    return {
      isOffline: false,
      storageUsed: 0,
      dataCount: 0,
      lastSync: null,
      pendingOperations: 0,
      cacheHitRate: 0,
      compressionRatio: 0,
    };
  }

  // Configuration management
  private async loadConfiguration(): Promise<void> {
    try {
      const configData = await AsyncStorage.getItem('offline_service_config');
      if (configData) {
        this.config = { ...this.config, ...JSON.parse(configData) };
      }
    } catch (error) {
      console.error('Failed to load configuration:', error);
    }
  }

  async updateConfiguration(newConfig: Partial<CacheConfig>): Promise<void> {
    this.config = { ...this.config, ...newConfig };
    try {
      await AsyncStorage.setItem('offline_service_config', JSON.stringify(this.config));
      console.log('Offline configuration updated');
    } catch (error) {
      console.error('Failed to save configuration:', error);
    }
  }

  getConfiguration(): CacheConfig {
    return { ...this.config };
  }

  getState(): OfflineState {
    return { ...this.state };
  }

  async exportOfflineData(): Promise<string> {
    try {
      const allData = await this.queryData();
      const exportData = {
        configuration: this.config,
        state: this.state,
        dataIndex: allData,
        exportDate: new Date().toISOString(),
      };

      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      console.error('Offline data export error:', error);
      throw error;
    }
  }

  async clearAllData(): Promise<void> {
    if (!this.db) return;

    try {
      await this.db.executeSql('DELETE FROM offline_data');
      await this.db.executeSql('DELETE FROM access_log');

      this.offlineData.clear();
      this.accessLog.clear();
      this.compressionCache.clear();

      await this.updateStorageStats();
      console.log('All offline data cleared');
    } catch (error) {
      console.error('Failed to clear offline data:', error);
    }
  }
}
