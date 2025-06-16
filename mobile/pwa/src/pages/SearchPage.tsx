import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Box,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  Typography,
  Chip,
  Button,
  IconButton,
  Tabs,
  Tab,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  DirectionsCar as CarIcon,
  Mic as MicIcon,
  FilterList as FilterIcon,
  Psychology as AIIcon,
} from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { searchVehicles } from '../store/slices/vehiclesSlice';
import { addNotification } from '../store/slices/uiSlice';
import { apiClient } from '../api/client';
import type { Vehicle } from '../types';

const SearchPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { isLoading } = useSelector((state: RootState) => state.vehicles);
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Vehicle[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [tabValue, setTabValue] = useState(0);
  const [isVoiceSearch, setIsVoiceSearch] = useState(false);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    try {
      // Try AI-powered search first
      if (tabValue === 1) {
        const nlpResponse = await apiClient.nlpQuery(searchQuery);
        if (nlpResponse.success) {
          setResults(nlpResponse.data.vehicles || []);
          dispatch(addNotification({
            type: 'success',
            message: `AI found ${nlpResponse.data.vehicles?.length || 0} results`,
          }));
          return;
        }
      }

      // Fallback to regular search
      const response = await dispatch(searchVehicles({ query: searchQuery }));
      if (searchVehicles.fulfilled.match(response)) {
        setResults(response.payload);
      }
    } catch (error) {
      dispatch(addNotification({
        type: 'error',
        message: 'Search failed. Please try again.',
      }));
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setQuery(value);

    // Generate suggestions
    if (value.length > 2) {
      const commonSuggestions = [
        `${value} impounded`,
        `${value} pending disposition`,
        `${value} released`,
        `make:${value}`,
        `license:${value}`,
        `vin:${value}`,
      ];
      setSuggestions(commonSuggestions);
    } else {
      setSuggestions([]);
    }
  };

  const handleVoiceSearch = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      setIsVoiceSearch(true);
      
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setQuery(transcript);
        handleSearch(transcript);
      };

      recognition.onerror = () => {
        dispatch(addNotification({
          type: 'error',
          message: 'Voice search failed. Please try again.',
        }));
      };

      recognition.onend = () => {
        setIsVoiceSearch(false);
      };

      recognition.start();
    } else {
      dispatch(addNotification({
        type: 'warning',
        message: 'Voice search is not supported in this browser.',
      }));
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    handleSearch(suggestion);
    setSuggestions([]);
  };

  const formatVehicleInfo = (vehicle: Vehicle) => {
    const parts = [];
    if (vehicle.make) parts.push(vehicle.make);
    if (vehicle.model) parts.push(vehicle.model);
    if (vehicle.year) parts.push(vehicle.year.toString());
    return parts.join(' ') || 'Unknown Vehicle';
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

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Search Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab icon={<SearchIcon />} label="Basic Search" />
          <Tab icon={<AIIcon />} label="AI Search" />
        </Tabs>
      </Box>

      {/* Search Input */}
      <Box sx={{ p: 2 }}>
        <TextField
          fullWidth
          placeholder={tabValue === 0 ? "Search by VIN, license, make, model..." : "Ask in natural language..."}
          value={query}
          onChange={handleInputChange}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch(query)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton 
                  onClick={handleVoiceSearch}
                  disabled={isVoiceSearch}
                  color={isVoiceSearch ? 'secondary' : 'default'}
                >
                  {isVoiceSearch ? <CircularProgress size={24} /> : <MicIcon />}
                </IconButton>
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

        {/* Search Button */}
        <Button
          fullWidth
          variant="contained"
          onClick={() => handleSearch(query)}
          disabled={!query.trim() || isLoading}
          sx={{ mt: 2, borderRadius: 3 }}
          startIcon={isLoading ? <CircularProgress size={20} /> : <SearchIcon />}
        >
          {isLoading ? 'Searching...' : tabValue === 0 ? 'Search' : 'Ask AI'}
        </Button>
      </Box>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <Box sx={{ px: 2, pb: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Suggestions
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {suggestions.map((suggestion, index) => (
              <Chip
                key={index}
                label={suggestion}
                variant="outlined"
                size="small"
                onClick={() => handleSuggestionClick(suggestion)}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Search Results */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {results.length > 0 ? (
          <List>
            {results.map((vehicle) => (
              <ListItem key={vehicle.id} button>
                <ListItemIcon>
                  <Avatar sx={{ bgcolor: 'primary.main' }}>
                    <CarIcon />
                  </Avatar>
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1">
                        {formatVehicleInfo(vehicle)}
                      </Typography>
                      <Chip
                        size="small"
                        label={vehicle.status || 'Unknown'}
                        color={getStatusColor(vehicle.status || '')}
                      />
                    </Box>
                  }
                  secondary={
                    <>
                      {vehicle.license_plate && (
                        <Typography variant="body2" color="text.secondary">
                          License: {vehicle.license_plate}
                        </Typography>
                      )}
                      {vehicle.vin && (
                        <Typography variant="body2" color="text.secondary">
                          VIN: {vehicle.vin}
                        </Typography>
                      )}
                      {vehicle.location && (
                        <Typography variant="body2" color="text.secondary">
                          Location: {vehicle.location}
                        </Typography>
                      )}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        ) : query && !isLoading ? (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No results found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try a different search term or use AI search for natural language queries
            </Typography>
          </Box>
        ) : !query ? (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              {tabValue === 0 ? 'Search Vehicles' : 'Ask AI'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {tabValue === 0 
                ? 'Enter VIN, license plate, make, model, or any vehicle information'
                : 'Ask questions like "Show me impounded Honda vehicles" or "What vehicles need disposition?"'
              }
            </Typography>
          </Box>
        ) : null}
      </Box>
    </Box>
  );
};

export default SearchPage;
