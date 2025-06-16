import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '../../api/client';
import type { Vehicle, SearchFilters } from '../../types';

interface VehiclesState {
  vehicles: Vehicle[];
  selectedVehicle: Vehicle | null;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  pagination: {
    page: number;
    totalPages: number;
    total: number;
    perPage: number;
  };
  filters: SearchFilters;
  searchQuery: string;
}

const initialState: VehiclesState = {
  vehicles: [],
  selectedVehicle: null,
  isLoading: false,
  isLoadingMore: false,
  error: null,
  pagination: {
    page: 1,
    totalPages: 1,
    total: 0,
    perPage: 20,
  },
  filters: {},
  searchQuery: '',
};

// Async thunks
export const fetchVehicles = createAsyncThunk(
  'vehicles/fetchVehicles',
  async ({ page = 1, perPage = 20, filters, reset = false }: {
    page?: number;
    perPage?: number;
    filters?: SearchFilters;
    reset?: boolean;
  }) => {
    const response = await apiClient.getVehicles(page, perPage, filters);
    if (response.success && response.data) {
      return { ...response.data, reset };
    }
    throw new Error(response.error || 'Failed to fetch vehicles');
  }
);

export const fetchVehicle = createAsyncThunk(
  'vehicles/fetchVehicle',
  async (id: number) => {
    const response = await apiClient.getVehicle(id);
    if (response.success && response.data) {
      return response.data;
    }
    throw new Error(response.error || 'Failed to fetch vehicle');
  }
);

export const updateVehicle = createAsyncThunk(
  'vehicles/updateVehicle',
  async ({ id, data }: { id: number; data: Partial<Vehicle> }) => {
    const response = await apiClient.updateVehicle(id, data);
    if (response.success && response.data) {
      return response.data;
    }
    throw new Error(response.error || 'Failed to update vehicle');
  }
);

export const searchVehicles = createAsyncThunk(
  'vehicles/searchVehicles',
  async ({ query, filters }: { query: string; filters?: SearchFilters }) => {
    const response = await apiClient.searchVehicles(query, filters);
    if (response.success && response.data) {
      return response.data;
    }
    throw new Error(response.error || 'Search failed');
  }
);

const vehiclesSlice = createSlice({
  name: 'vehicles',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setFilters: (state, action: PayloadAction<SearchFilters>) => {
      state.filters = action.payload;
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    clearSelectedVehicle: (state) => {
      state.selectedVehicle = null;
    },
    updateVehicleInList: (state, action: PayloadAction<Vehicle>) => {
      const index = state.vehicles.findIndex((v: Vehicle) => v.id === action.payload.id);
      if (index !== -1) {
        state.vehicles[index] = action.payload;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch vehicles
      .addCase(fetchVehicles.pending, (state, action) => {
        if (action.meta.arg.reset) {
          state.isLoading = true;
        } else {
          state.isLoadingMore = true;
        }
        state.error = null;
      })
      .addCase(fetchVehicles.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        
        if (action.payload.reset) {
          state.vehicles = action.payload.data || action.payload;
        } else {
          state.vehicles.push(...(action.payload.data || action.payload));
        }
        
        state.pagination = {
          page: action.payload.page || 1,
          totalPages: action.payload.totalPages || 1,
          total: action.payload.total || state.vehicles.length,
          perPage: action.payload.perPage || 20,
        };
      })
      .addCase(fetchVehicles.rejected, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        state.error = action.error.message || 'Failed to fetch vehicles';
      })
      // Fetch single vehicle
      .addCase(fetchVehicle.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchVehicle.fulfilled, (state, action) => {
        state.isLoading = false;
        state.selectedVehicle = action.payload;
      })
      .addCase(fetchVehicle.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch vehicle';
      })
      // Update vehicle
      .addCase(updateVehicle.fulfilled, (state, action) => {
        const index = state.vehicles.findIndex((v: Vehicle) => v.id === action.payload.id);
        if (index !== -1) {
          state.vehicles[index] = action.payload;
        }
        if (state.selectedVehicle?.id === action.payload.id) {
          state.selectedVehicle = action.payload;
        }
      })
      // Search vehicles
      .addCase(searchVehicles.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(searchVehicles.fulfilled, (state, action) => {
        state.isLoading = false;
        state.vehicles = action.payload;
      })
      .addCase(searchVehicles.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Search failed';
      });
  },
});

export const {
  clearError,
  setFilters,
  setSearchQuery,
  clearSelectedVehicle,
  updateVehicleInList,
} = vehiclesSlice.actions;

export default vehiclesSlice.reducer;
