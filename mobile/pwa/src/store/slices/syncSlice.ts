import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { OfflineAction, SyncStatus } from '../../types';

interface SyncState {
  status: SyncStatus;
  offlineActions: OfflineAction[];
  isOnline: boolean;
  lastSyncAttempt: string | null;
}

const initialState: SyncState = {
  status: {
    lastSync: '',
    pendingActions: 0,
    isOnline: navigator.onLine,
    isSyncing: false,
  },
  offlineActions: [],
  isOnline: navigator.onLine,
  lastSyncAttempt: null,
};

const syncSlice = createSlice({
  name: 'sync',
  initialState,
  reducers: {
    setOnlineStatus: (state, action: PayloadAction<boolean>) => {
      state.isOnline = action.payload;
      state.status.isOnline = action.payload;
    },
    addOfflineAction: (state, action: PayloadAction<OfflineAction>) => {
      state.offlineActions.push(action.payload);
      state.status.pendingActions = state.offlineActions.length;
    },
    removeOfflineAction: (state, action: PayloadAction<string>) => {
      state.offlineActions = state.offlineActions.filter(
        (offlineAction: OfflineAction) => offlineAction.id !== action.payload
      );
      state.status.pendingActions = state.offlineActions.length;
    },
    setSyncStatus: (state, action: PayloadAction<Partial<SyncStatus>>) => {
      state.status = { ...state.status, ...action.payload };
    },
    startSync: (state) => {
      state.status.isSyncing = true;
      state.lastSyncAttempt = new Date().toISOString();
    },
    completeSync: (state, action: PayloadAction<{ success: boolean; syncedCount?: number }>) => {
      state.status.isSyncing = false;
      if (action.payload.success) {
        state.status.lastSync = new Date().toISOString();
        // Remove synced actions
        if (action.payload.syncedCount) {
          state.offlineActions = state.offlineActions.slice(action.payload.syncedCount);
          state.status.pendingActions = state.offlineActions.length;
        }
      }
    },
    clearOfflineActions: (state) => {
      state.offlineActions = [];
      state.status.pendingActions = 0;
    },
  },
});

export const {
  setOnlineStatus,
  addOfflineAction,
  removeOfflineAction,
  setSyncStatus,
  startSync,
  completeSync,
  clearOfflineActions,
} = syncSlice.actions;

export default syncSlice.reducer;
