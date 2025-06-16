// Shared TypeScript interfaces for the iTow VMS mobile applications

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

export interface AIInsight {
  id: string;
  vehicleId: number;
  type: 'disposition' | 'timeline' | 'revenue' | 'anomaly';
  prediction: any;
  confidence: number;
  explanation: string;
  createdAt: string;
}

export interface WorkflowStage {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  assignedTo?: string;
  dueDate?: string;
  completedAt?: string;
  notes?: string;
}

export interface Document {
  id: string;
  vehicleId: number;
  type: 'registration' | 'title' | 'license' | 'photo' | 'other';
  filename: string;
  url: string;
  uploadedAt: string;
  extractedData?: Record<string, any>;
  aiProcessed?: boolean;
}

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  vehicleId?: number;
  actionUrl?: string;
  read: boolean;
  createdAt: string;
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

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
}

export interface VehicleStats {
  total: number;
  byStatus: Record<string, number>;
  byJurisdiction: Record<string, number>;
  totalValue: number;
  totalFees: number;
  averageStorageDays: number;
}

export interface DashboardData {
  vehicleStats: VehicleStats;
  recentVehicles: Vehicle[];
  urgentItems: Vehicle[];
  aiInsights: AIInsight[];
  notifications: Notification[];
}

// Mobile-specific interfaces
export interface OfflineAction {
  id: string;
  type: 'create' | 'update' | 'delete';
  entity: 'vehicle' | 'document' | 'note';
  payload: any;
  timestamp: string;
  synced: boolean;
}

export interface CameraCapture {
  uri: string;
  base64?: string;
  type: 'photo' | 'document';
  metadata?: {
    location?: {
      latitude: number;
      longitude: number;
    };
    timestamp: string;
  };
}

export interface SyncStatus {
  lastSync: string;
  pendingActions: number;
  isOnline: boolean;
  isSyncing: boolean;
}
