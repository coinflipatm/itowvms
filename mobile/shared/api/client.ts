// Shared API client for iTow VMS mobile applications
import axios, { AxiosInstance } from 'axios';
import type { 
  Vehicle, 
  User, 
  ApiResponse, 
  PaginatedResponse, 
  SearchFilters,
  DashboardData,
  AIInsight,
  Document
} from '../types';

export class ITowAPIClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config: any) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error: any) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: any) => response,
      (error: any) => {
        if (error.response?.status === 401) {
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  private handleAuthError() {
    this.clearToken();
    // Emit auth error event for app to handle
    window.dispatchEvent(new CustomEvent('auth-error'));
  }

  // Authentication
  async login(username: string, password: string): Promise<ApiResponse<{ user: User; token: string }>> {
    const response = await this.client.post('/auth/login', { username, password });
    return response.data;
  }

  async logout(): Promise<ApiResponse<void>> {
    const response = await this.client.post('/auth/logout');
    this.clearToken();
    return response.data;
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Vehicles
  async getVehicles(
    page: number = 1,
    perPage: number = 20,
    filters?: SearchFilters
  ): Promise<ApiResponse<PaginatedResponse<Vehicle>>> {
    const params = { page, per_page: perPage, ...filters };
    const response = await this.client.get('/vehicles', { params });
    return response.data;
  }

  async getVehicle(id: number): Promise<ApiResponse<Vehicle>> {
    const response = await this.client.get(`/vehicles/${id}`);
    return response.data;
  }

  async updateVehicle(id: number, data: Partial<Vehicle>): Promise<ApiResponse<Vehicle>> {
    const response = await this.client.put(`/vehicles/${id}`, data);
    return response.data;
  }

  async deleteVehicle(id: number): Promise<ApiResponse<void>> {
    const response = await this.client.delete(`/vehicles/${id}`);
    return response.data;
  }

  // Search
  async searchVehicles(query: string, filters?: SearchFilters): Promise<ApiResponse<Vehicle[]>> {
    const response = await this.client.post('/vehicles/search', { query, filters });
    return response.data;
  }

  // Dashboard
  async getDashboardData(): Promise<ApiResponse<DashboardData>> {
    const response = await this.client.get('/dashboard');
    return response.data;
  }

  // AI Features
  async getAIInsights(vehicleId: number): Promise<ApiResponse<AIInsight[]>> {
    const response = await this.client.get(`/ai/insights/${vehicleId}`);
    return response.data;
  }

  async processWithAI(vehicleId: number, type: string): Promise<ApiResponse<AIInsight>> {
    const response = await this.client.post(`/ai/process`, { vehicle_id: vehicleId, type });
    return response.data;
  }

  async nlpQuery(query: string): Promise<ApiResponse<any>> {
    const response = await this.client.post('/ai/nlp/query', { query });
    return response.data;
  }

  // Documents
  async uploadDocument(
    vehicleId: number, 
    file: File | Blob, 
    type: string
  ): Promise<ApiResponse<Document>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('vehicle_id', vehicleId.toString());
    formData.append('type', type);

    const response = await this.client.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getDocuments(vehicleId: number): Promise<ApiResponse<Document[]>> {
    const response = await this.client.get(`/documents/vehicle/${vehicleId}`);
    return response.data;
  }

  async processDocumentAI(documentId: string): Promise<ApiResponse<any>> {
    const response = await this.client.post(`/ai/document/process/${documentId}`);
    return response.data;
  }

  // Workflow
  async updateWorkflowStage(vehicleId: number, stage: string, data: any): Promise<ApiResponse<void>> {
    const response = await this.client.post(`/workflow/${vehicleId}/stage/${stage}`, data);
    return response.data;
  }

  // Sync for offline support
  async syncOfflineActions(actions: any[]): Promise<ApiResponse<any>> {
    const response = await this.client.post('/sync/actions', { actions });
    return response.data;
  }

  async getUpdates(since: string): Promise<ApiResponse<any>> {
    const response = await this.client.get('/sync/updates', { params: { since } });
    return response.data;
  }
}

// Create default instance
export const apiClient = new ITowAPIClient();

// Utility functions
export const handleApiError = (error: any): string => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

export const isNetworkError = (error: any): boolean => {
  return !error.response && error.request;
};

export default ITowAPIClient;
