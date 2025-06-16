// Local types for PWA (simplified version)
export interface Vehicle {
  id: number;
  vin?: string;
  license_plate?: string;
  make?: string;
  model?: string;
  year?: number;
  color?: string;
  tow_date?: string;
  location?: string;
  jurisdiction?: string;
  status?: string;
  stage?: string;
  disposition?: string;
  lot_location?: string;
  estimated_value?: number;
  storage_fees?: number;
  total_fees?: number;
  release_eligibility?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  permissions: string[];
  lastLogin?: string;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface SearchFilters {
  status?: string[];
  jurisdiction?: string[];
  make?: string[];
  dateRange?: {
    start: string;
    end: string;
  };
  valueRange?: {
    min: number;
    max: number;
  };
  textSearch?: string;
}

export interface OfflineAction {
  id: string;
  type: 'create' | 'update' | 'delete';
  entity: 'vehicle' | 'document' | 'note';
  payload: any;
  timestamp: string;
  synced: boolean;
}

export interface SyncStatus {
  lastSync: string;
  pendingActions: number;
  isOnline: boolean;
  isSyncing: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
}

export interface AIInsight {
  id: string;
  type: string;
  title: string;
  description: string;
  explanation: string;
  confidence: number;
  data: any;
  created_at: string;
  vehicle_id: number;
}

export interface Document {
  id: string;
  vehicle_id: number;
  type: string;
  filename: string;
  url: string;
  size: number;
  uploaded_at: string;
  processed: boolean;
  metadata?: any;
}
