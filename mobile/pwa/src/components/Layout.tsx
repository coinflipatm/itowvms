import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  BottomNavigation,
  BottomNavigationAction,
  Badge,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  DirectionsCar as VehiclesIcon,
  Search as SearchIcon,
  Person as ProfileIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  CameraAlt as CameraIcon,
} from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { setBottomNavValue, showCameraModal } from '../store/slices/uiSlice';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  
  const { bottomNavValue } = useSelector((state: RootState) => state.ui);
  const { status } = useSelector((state: RootState) => state.sync);

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/dashboard':
        return 'Dashboard';
      case '/vehicles':
        return 'Vehicles';
      case '/search':
        return 'Search';
      case '/profile':
        return 'Profile';
      default:
        if (location.pathname.startsWith('/vehicles/')) {
          return 'Vehicle Details';
        }
        return 'iTow VMS';
    }
  };

  const handleBottomNavChange = (_event: React.SyntheticEvent, newValue: number) => {
    dispatch(setBottomNavValue(newValue));
    
    const routes = ['/dashboard', '/vehicles', '/search', '/profile'];
    navigate(routes[newValue]);
  };

  const handleCameraClick = () => {
    dispatch(showCameraModal());
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* App Bar */}
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="menu"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {getPageTitle()}
          </Typography>

          {/* Sync Status Indicator */}
          {status.pendingActions > 0 && (
            <Badge badgeContent={status.pendingActions} color="warning">
              <NotificationsIcon />
            </Badge>
          )}

          {/* Camera Button */}
          <IconButton color="inherit" onClick={handleCameraClick}>
            <CameraIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          pb: isMobile ? 7 : 0, // Bottom nav height
          backgroundColor: theme.palette.background.default,
        }}
      >
        {children}
      </Box>

      {/* Bottom Navigation (Mobile Only) */}
      {isMobile && (
        <BottomNavigation
          value={bottomNavValue}
          onChange={handleBottomNavChange}
          sx={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            borderTop: 1,
            borderColor: 'divider',
            backgroundColor: 'background.paper',
          }}
        >
          <BottomNavigationAction
            label="Dashboard"
            icon={<DashboardIcon />}
          />
          <BottomNavigationAction
            label="Vehicles"
            icon={<VehiclesIcon />}
          />
          <BottomNavigationAction
            label="Search"
            icon={<SearchIcon />}
          />
          <BottomNavigationAction
            label="Profile"
            icon={<ProfileIcon />}
          />
        </BottomNavigation>
      )}

      {/* Offline Indicator */}
      {!status.isOnline && (
        <Box
          sx={{
            position: 'fixed',
            bottom: isMobile ? 70 : 20,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'warning.main',
            color: 'warning.contrastText',
            px: 2,
            py: 1,
            borderRadius: 2,
            fontSize: '0.875rem',
            zIndex: theme.zIndex.snackbar,
          }}
        >
          Offline Mode - {status.pendingActions} pending actions
        </Box>
      )}
    </Box>
  );
};

export default Layout;
