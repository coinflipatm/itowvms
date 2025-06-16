import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Avatar,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Switch,
  Divider,
  Button,
  Chip,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  DarkMode as DarkModeIcon,
  Language as LanguageIcon,
  Security as SecurityIcon,
  Sync as SyncIcon,
  ExitToApp as LogoutIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { logoutUser } from '../store/slices/authSlice';
import { setTheme } from '../store/slices/uiSlice';

const ProfilePage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { user } = useSelector((state: RootState) => state.auth);
  const { theme } = useSelector((state: RootState) => state.ui);
  const { status } = useSelector((state: RootState) => state.sync);

  const handleLogout = () => {
    dispatch(logoutUser());
  };

  const handleThemeToggle = () => {
    dispatch(setTheme(theme === 'light' ? 'dark' : 'light'));
  };

  const formatLastSync = () => {
    if (!status.lastSync) return 'Never';
    return new Date(status.lastSync).toLocaleString();
  };

  return (
    <Box sx={{ p: 2 }}>
      {/* User Profile Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ textAlign: 'center', py: 4 }}>
          <Avatar
            sx={{
              width: 80,
              height: 80,
              mx: 'auto',
              mb: 2,
              bgcolor: 'primary.main',
              fontSize: '2rem',
            }}
          >
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </Avatar>
          
          <Typography variant="h5" gutterBottom>
            {user?.username || 'Unknown User'}
          </Typography>
          
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {user?.email || 'No email'}
          </Typography>
          
          <Chip
            label={user?.role || 'Unknown Role'}
            color="primary"
            variant="outlined"
            sx={{ mt: 1 }}
          />
        </CardContent>
      </Card>

      {/* Settings */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Settings
          </Typography>
          
          <List disablePadding>
            <ListItem>
              <ListItemIcon>
                <NotificationsIcon />
              </ListItemIcon>
              <ListItemText
                primary="Push Notifications"
                secondary="Receive alerts for important updates"
              />
              <Switch defaultChecked />
            </ListItem>
            
            <Divider />
            
            <ListItem>
              <ListItemIcon>
                <DarkModeIcon />
              </ListItemIcon>
              <ListItemText
                primary="Dark Mode"
                secondary="Switch between light and dark themes"
              />
              <Switch
                checked={theme === 'dark'}
                onChange={handleThemeToggle}
              />
            </ListItem>
            
            <Divider />
            
            <ListItem button>
              <ListItemIcon>
                <LanguageIcon />
              </ListItemIcon>
              <ListItemText
                primary="Language"
                secondary="English (US)"
              />
            </ListItem>
            
            <Divider />
            
            <ListItem button>
              <ListItemIcon>
                <SecurityIcon />
              </ListItemIcon>
              <ListItemText
                primary="Security"
                secondary="Manage your security settings"
              />
            </ListItem>
          </List>
        </CardContent>
      </Card>

      {/* Sync Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sync Status
          </Typography>
          
          <List disablePadding>
            <ListItem>
              <ListItemIcon>
                <SyncIcon color={status.isOnline ? 'success' : 'error'} />
              </ListItemIcon>
              <ListItemText
                primary={status.isOnline ? 'Online' : 'Offline'}
                secondary={`Last sync: ${formatLastSync()}`}
              />
              {status.pendingActions > 0 && (
                <Chip
                  size="small"
                  label={`${status.pendingActions} pending`}
                  color="warning"
                />
              )}
            </ListItem>
          </List>
        </CardContent>
      </Card>

      {/* App Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            App Information
          </Typography>
          
          <List disablePadding>
            <ListItem>
              <ListItemIcon>
                <InfoIcon />
              </ListItemIcon>
              <ListItemText
                primary="Version"
                secondary="1.0.0 (PWA)"
              />
            </ListItem>
            
            <ListItem button>
              <ListItemIcon>
                <InfoIcon />
              </ListItemIcon>
              <ListItemText
                primary="About iTow VMS"
                secondary="Learn more about the app"
              />
            </ListItem>
          </List>
        </CardContent>
      </Card>

      {/* Logout */}
      <Button
        fullWidth
        variant="outlined"
        color="error"
        startIcon={<LogoutIcon />}
        onClick={handleLogout}
        sx={{ borderRadius: 3 }}
      >
        Sign Out
      </Button>
    </Box>
  );
};

export default ProfilePage;
