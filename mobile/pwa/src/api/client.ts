// Simplified API client for PWA
import axios, { AxiosInstance } from 'axios';
import type { Vehicle, User, APIResponse, SearchFilters } from '../types';

class ITowAPIClient {
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
  }

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  // Authentication
  async login(username: string, password: string): Promise<APIResponse<{ user: User; token: string }>> {
    const response = await this.client.post('/auth/login', { username, password });
    return response.data;
  }

  async logout(): Promise<APIResponse<void>> {
    const response = await this.client.post('/auth/logout');
    this.clearToken();
    return response.data;
  }

  async getCurrentUser(): Promise<APIResponse<User>> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  // Vehicles
  async getVehicles(page: number = 1, perPage: number = 20, filters?: SearchFilters): Promise<APIResponse<any>> {
    const params = { page, per_page: perPage, ...filters };
    const response = await this.client.get('/vehicles', { params });
    return response.data;
  }

  async getVehicle(id: number): Promise<APIResponse<Vehicle>> {
    const response = await this.client.get(`/vehicles/${id}`);
    return response.data;
  }

  async updateVehicle(id: number, data: Partial<Vehicle>): Promise<APIResponse<Vehicle>> {
    const response = await this.client.put(`/vehicles/${id}`, data);
    return response.data;
  }

  // Dashboard
  async getDashboardData(): Promise<APIResponse<any>> {
    const response = await this.client.get('/dashboard');
    return response.data;
  }

  // Search
  async searchVehicles(query: string, filters?: SearchFilters): Promise<APIResponse<Vehicle[]>> {
    const response = await this.client.post('/vehicles/search', { query, filters });
    return response.data;
  }

  // AI Features
  async nlpQuery(query: string): Promise<APIResponse<any>> {
    const response = await this.client.post('/ai/nlp/query', { query });
    return response.data;
  }

  async getAIInsights(vehicleId: number): Promise<APIResponse<any[]>> {
    const response = await this.client.get(`/ai/insights/${vehicleId}`);
    return response.data;
  }

  async processWithAI(vehicleId: number, type: string): Promise<APIResponse<any>> {
    const response = await this.client.post(`/ai/process`, { vehicle_id: vehicleId, type });
    return response.data;
  }

  // Documents
  async getDocuments(vehicleId: number): Promise<APIResponse<any[]>> {
    const response = await this.client.get(`/documents/vehicle/${vehicleId}`);
    return response.data;
  }
}

export const apiClient = new ITowAPIClient();
export default ITowAPIClient;
