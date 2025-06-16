import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Snackbar, Alert } from '@mui/material';

import { RootState, AppDispatch } from './store';
import { getCurrentUser } from './store/slices/authSlice';
import { removeNotification } from './store/slices/uiSlice';
import { setOnlineStatus } from './store/slices/syncSlice';

// Components
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import VehiclesPage from './pages/VehiclesPage';
import VehicleDetailsPage from './pages/VehicleDetailsPage';
import SearchPage from './pages/SearchPage';
import ProfilePage from './pages/ProfilePage';
import OfflinePage from './pages/OfflinePage';

// Hooks
import { useNetworkStatus } from './hooks/useNetworkStatus';

function App() {
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, token } = useSelector((state: RootState) => state.auth);
  const { notifications } = useSelector((state: RootState) => state.ui);
  const { isOnline } = useSelector((state: RootState) => state.sync);
  
  const networkStatus = useNetworkStatus();

  useEffect(() => {
    // Update online status
    dispatch(setOnlineStatus(networkStatus));
  }, [networkStatus, dispatch]);

  useEffect(() => {
    // Check authentication on app load
    if (token && !isAuthenticated) {
      dispatch(getCurrentUser());
    }
  }, [token, isAuthenticated, dispatch]);

  useEffect(() => {
    // Handle auth errors
    const handleAuthError = () => {
      // Redirect to login or show auth error
    };

    window.addEventListener('auth-error', handleAuthError);
    return () => window.removeEventListener('auth-error', handleAuthError);
  }, []);

  const handleCloseNotification = (id: string) => {
    dispatch(removeNotification(id));
  };

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (!isOnline) {
    return <OfflinePage />;
  }

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/vehicles" element={<VehiclesPage />} />
          <Route path="/vehicles/:id" element={<VehicleDetailsPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Layout>

      {/* Notifications */}
      {notifications.map((notification) => (
        <Snackbar
          key={notification.id}
          open={true}
          autoHideDuration={notification.autoHide !== false ? 6000 : null}
          onClose={() => handleCloseNotification(notification.id)}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert
            onClose={() => handleCloseNotification(notification.id)}
            severity={notification.type}
            sx={{ width: '100%' }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      ))}
    </Box>
  );
}

export default App;
