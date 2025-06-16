import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  theme: 'light' | 'dark';
  bottomNavValue: number;
  isDrawerOpen: boolean;
  showCameraModal: boolean;
  showSearchModal: boolean;
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    autoHide?: boolean;
  }>;
  loading: {
    [key: string]: boolean;
  };
}

const initialState: UIState = {
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  bottomNavValue: 0,
  isDrawerOpen: false,
  showCameraModal: false,
  showSearchModal: false,
  notifications: [],
  loading: {},
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
      localStorage.setItem('theme', action.payload);
    },
    setBottomNavValue: (state, action: PayloadAction<number>) => {
      state.bottomNavValue = action.payload;
    },
    toggleDrawer: (state) => {
      state.isDrawerOpen = !state.isDrawerOpen;
    },
    setDrawerOpen: (state, action: PayloadAction<boolean>) => {
      state.isDrawerOpen = action.payload;
    },
    showCameraModal: (state) => {
      state.showCameraModal = true;
    },
    hideCameraModal: (state) => {
      state.showCameraModal = false;
    },
    showSearchModal: (state) => {
      state.showSearchModal = true;
    },
    hideSearchModal: (state) => {
      state.showSearchModal = false;
    },
    addNotification: (state, action: PayloadAction<{
      type: 'success' | 'error' | 'warning' | 'info';
      message: string;
      autoHide?: boolean;
    }>) => {
      const notification = {
        id: Date.now().toString(),
        ...action.payload,
      };
      state.notifications.push(notification);
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
    setLoading: (state, action: PayloadAction<{ key: string; loading: boolean }>) => {
      state.loading[action.payload.key] = action.payload.loading;
    },
    clearLoading: (state, action: PayloadAction<string>) => {
      delete state.loading[action.payload];
    },
  },
});

export const {
  setTheme,
  setBottomNavValue,
  toggleDrawer,
  setDrawerOpen,
  showCameraModal,
  hideCameraModal,
  showSearchModal,
  hideSearchModal,
  addNotification,
  removeNotification,
  clearNotifications,
  setLoading,
  clearLoading,
} = uiSlice.actions;

export default uiSlice.reducer;
