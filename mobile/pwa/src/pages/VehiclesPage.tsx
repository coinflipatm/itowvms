import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  IconButton,
  Fab,
  TextField,
  InputAdornment,
  Menu,
  MenuItem,
  Button,
  CircularProgress,
  Avatar,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  DirectionsCar as CarIcon,
  MoreVert as MoreVertIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { 
  fetchVehicles, 
  setSearchQuery
} from '../store/slices/vehiclesSlice';
import type { Vehicle } from '../types';

const VehiclesPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  
  const { 
    vehicles, 
    isLoading, 
    isLoadingMore, 
    error, 
    pagination, 
    filters, 
    searchQuery 
  } = useSelector((state: RootState) => state.vehicles);

  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);

  useEffect(() => {
    // Load vehicles on component mount
    dispatch(fetchVehicles({ page: 1, reset: true }));
  }, [dispatch]);

  const handleSearch = (query: string) => {
    dispatch(setSearchQuery(query));
    dispatch(fetchVehicles({ page: 1, reset: true, filters: { ...filters, textSearch: query } }));
  };

  const handleSearchInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const query = event.target.value;
    setLocalSearchQuery(query);
    
    // Debounced search
    const timeoutId = setTimeout(() => {
      handleSearch(query);
    }, 500);

    return () => clearTimeout(timeoutId);
  };

  const handleVehicleClick = (vehicle: Vehicle) => {
    navigate(`/vehicles/${vehicle.id}`);
  };

  const handleMoreClick = (event: React.MouseEvent<HTMLElement>, vehicle: Vehicle) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedVehicle(vehicle);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedVehicle(null);
  };

  const handleRefresh = () => {
    dispatch(fetchVehicles({ page: 1, reset: true, filters }));
  };

  const handleLoadMore = () => {
    if (!isLoadingMore && pagination.page < pagination.totalPages) {
      dispatch(fetchVehicles({ 
        page: pagination.page + 1, 
        reset: false, 
        filters 
      }));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'impounded':
        return 'error';
      case 'pending_disposition':
        return 'warning';
      case 'released':
        return 'success';
      case 'disposed':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number | undefined) => {
    if (!amount) return '$0';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Search Header */}
      <Box sx={{ p: 2, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
        <TextField
          fullWidth
          placeholder="Search vehicles..."
          value={localSearchQuery}
          onChange={handleSearchInputChange}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton>
                  <FilterIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
          sx={{ 
            '& .MuiOutlinedInput-root': { 
              borderRadius: 3 
            } 
          }}
        />
      </Box>

      {/* Vehicles List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading && vehicles.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ p: 2 }}>
            <Card>
              <CardContent>
                <Typography color="error" gutterBottom>
                  Error loading vehicles
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {error}
                </Typography>
                <Button onClick={handleRefresh} startIcon={<RefreshIcon />}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          </Box>
        ) : (
          <>
            <List disablePadding>
              {vehicles.map((vehicle) => (
                <ListItem
                  key={vehicle.id}
                  button
                  onClick={() => handleVehicleClick(vehicle)}
                  sx={{ 
                    borderBottom: 1, 
                    borderColor: 'divider',
                    py: 2,
                  }}
                >
                  <Avatar 
                    sx={{ 
                      mr: 2, 
                      bgcolor: 'primary.main',
                      width: 48,
                      height: 48,
                    }}
                  >
                    <CarIcon />
                  </Avatar>
                  
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {vehicle.make} {vehicle.model}
                        </Typography>
                        <Chip
                          size="small"
                          label={vehicle.status || 'Unknown'}
                          color={getStatusColor(vehicle.status || '')}
                        />
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">
                          {vehicle.license_plate || 'No License'} • {vehicle.year || 'Unknown Year'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Value: {formatCurrency(vehicle.estimated_value)} • 
                          Towed: {formatDate(vehicle.tow_date)}
                        </Typography>
                      </Box>
                    }
                  />
                  
                  <ListItemSecondaryAction>
                    <IconButton 
                      onClick={(e) => handleMoreClick(e, vehicle)}
                      edge="end"
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>

            {/* Load More */}
            {pagination.page < pagination.totalPages && (
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Button 
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  startIcon={isLoadingMore ? <CircularProgress size={20} /> : null}
                >
                  {isLoadingMore ? 'Loading...' : 'Load More'}
                </Button>
              </Box>
            )}

            {/* Empty State */}
            {vehicles.length === 0 && !isLoading && (
              <Box sx={{ textAlign: 'center', p: 4 }}>
                <CarIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No vehicles found
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Try adjusting your search or filters
                </Typography>
              </Box>
            )}
          </>
        )}
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          if (selectedVehicle) {
            navigate(`/vehicles/${selectedVehicle.id}`);
          }
          handleMenuClose();
        }}>
          View Details
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          Edit Vehicle
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          Process with AI
        </MenuItem>
      </Menu>

      {/* Floating Action Button */}
      <Fab
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 80, // Above bottom navigation
          right: 16,
        }}
      >
        <AddIcon />
      </Fab>
    </Box>
  );
};

export default VehiclesPage;
