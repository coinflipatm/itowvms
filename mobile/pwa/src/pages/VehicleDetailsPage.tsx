import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Grid,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Avatar,
  Tab,
  Tabs,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Share as ShareIcon,
  DirectionsCar as CarIcon,
  AttachMoney as MoneyIcon,
  Schedule as ScheduleIcon,
  Psychology as AIIcon,
  CameraAlt as CameraIcon,
  Assignment as DocumentIcon,
} from '@mui/icons-material';

import { RootState, AppDispatch } from '../store';
import { fetchVehicle } from '../store/slices/vehiclesSlice';
import { addNotification } from '../store/slices/uiSlice';
import { apiClient } from '../api/client';
import type { AIInsight, Document } from '../types';

const VehicleDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  
  const { selectedVehicle, isLoading, error } = useSelector((state: RootState) => state.vehicles);
  
  const [tabValue, setTabValue] = useState(0);
  const [aiInsights, setAIInsights] = useState<AIInsight[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [processingAI, setProcessingAI] = useState(false);

  useEffect(() => {
    if (id) {
      dispatch(fetchVehicle(parseInt(id)));
      loadAIInsights(parseInt(id));
      loadDocuments(parseInt(id));
    }
  }, [id, dispatch]);

  const loadAIInsights = async (vehicleId: number) => {
    try {
      const response = await apiClient.getAIInsights(vehicleId);
      if (response.success && response.data) {
        setAIInsights(response.data);
      }
    } catch (error) {
      console.error('Failed to load AI insights:', error);
    }
  };

  const loadDocuments = async (vehicleId: number) => {
    try {
      const response = await apiClient.getDocuments(vehicleId);
      if (response.success && response.data) {
        setDocuments(response.data);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleProcessWithAI = async (type: string) => {
    if (!selectedVehicle) return;
    
    setProcessingAI(true);
    try {
      const response = await apiClient.processWithAI(selectedVehicle.id, type);
      if (response.success) {
        dispatch(addNotification({
          type: 'success',
          message: `AI ${type} processing completed`,
        }));
        loadAIInsights(selectedVehicle.id);
      }
    } catch (error) {
      dispatch(addNotification({
        type: 'error',
        message: `AI processing failed: ${error}`,
      }));
    } finally {
      setProcessingAI(false);
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
    return new Date(dateString).toLocaleString();
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

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !selectedVehicle) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error" action={
          <Button onClick={() => navigate('/vehicles')}>
            Back to Vehicles
          </Button>
        }>
          {error || 'Vehicle not found'}
        </Alert>
      </Box>
    );
  }

  const renderOverviewTab = () => (
    <Box sx={{ p: 2 }}>
      {/* Vehicle Header */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ bgcolor: 'primary.main', mr: 2, width: 56, height: 56 }}>
              <CarIcon sx={{ fontSize: 28 }} />
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h5" gutterBottom>
                {selectedVehicle.make} {selectedVehicle.model}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip
                  label={selectedVehicle.status || 'Unknown'}
                  color={getStatusColor(selectedVehicle.status || '')}
                />
                {selectedVehicle.stage && (
                  <Chip label={selectedVehicle.stage} variant="outlined" />
                )}
              </Box>
            </Box>
          </Box>
          
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                License Plate
              </Typography>
              <Typography variant="body1">
                {selectedVehicle.license_plate || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                Year
              </Typography>
              <Typography variant="body1">
                {selectedVehicle.year || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                Color
              </Typography>
              <Typography variant="body1">
                {selectedVehicle.color || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2" color="text.secondary">
                VIN
              </Typography>
              <Typography variant="body1" sx={{ fontSize: '0.875rem' }}>
                {selectedVehicle.vin || 'N/A'}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Financial Information */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Financial Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <MoneyIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Estimated Value
                </Typography>
              </Box>
              <Typography variant="h6">
                {formatCurrency(selectedVehicle.estimated_value)}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <MoneyIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Storage Fees
                </Typography>
              </Box>
              <Typography variant="h6">
                {formatCurrency(selectedVehicle.storage_fees)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Location & Timeline */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Location & Timeline
          </Typography>
          <List disablePadding>
            <ListItem disablePadding>
              <ListItemText
                primary="Current Location"
                secondary={selectedVehicle.lot_location || selectedVehicle.location || 'N/A'}
                primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
              />
            </ListItem>
            <ListItem disablePadding>
              <ListItemText
                primary="Tow Date"
                secondary={formatDate(selectedVehicle.tow_date)}
                primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
              />
            </ListItem>
            <ListItem disablePadding>
              <ListItemText
                primary="Last Updated"
                secondary={formatDate(selectedVehicle.updated_at)}
                primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
              />
            </ListItem>
          </List>
        </CardContent>
      </Card>
    </Box>
  );

  const renderAITab = () => (
    <Box sx={{ p: 2 }}>
      {/* AI Actions */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            AI Processing
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => handleProcessWithAI('disposition')}
                disabled={processingAI}
                startIcon={processingAI ? <CircularProgress size={16} /> : <AIIcon />}
              >
                Predict Disposition
              </Button>
            </Grid>
            <Grid item xs={6}>
              <Button
                fullWidth
                variant="outlined"
                onClick={() => handleProcessWithAI('timeline')}
                disabled={processingAI}
                startIcon={processingAI ? <CircularProgress size={16} /> : <ScheduleIcon />}
              >
                Timeline Analysis
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* AI Insights */}
      {aiInsights.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              AI Insights
            </Typography>
            {aiInsights.map((insight) => (
              <Card key={insight.id} variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Chip size="small" label={insight.type} color="primary" sx={{ mr: 1 }} />
                    <Typography variant="body2" color="text.secondary">
                      {Math.round(insight.confidence * 100)}% confidence
                    </Typography>
                  </Box>
                  <Typography variant="body2">
                    {insight.explanation}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
      )}
    </Box>
  );

  const renderDocumentsTab = () => (
    <Box sx={{ p: 2 }}>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Documents
            </Typography>
            <IconButton color="primary">
              <CameraIcon />
            </IconButton>
          </Box>
          
          {documents.length > 0 ? (
            <List>
              {documents.map((doc) => (
                <ListItem key={doc.id} divider>
                  <DocumentIcon sx={{ mr: 2 }} />
                  <ListItemText
                    primary={doc.filename}
                    secondary={`${doc.type} • ${formatDate(doc.uploaded_at)}`}
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <DocumentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No documents uploaded
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        p: 2, 
        bgcolor: 'background.paper',
        borderBottom: 1,
        borderColor: 'divider'
      }}>
        <IconButton onClick={() => navigate('/vehicles')} sx={{ mr: 1 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h6" sx={{ flex: 1 }}>
          Vehicle Details
        </Typography>
        <IconButton>
          <EditIcon />
        </IconButton>
        <IconButton>
          <ShareIcon />
        </IconButton>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Overview" />
          <Tab label="AI Insights" />
          <Tab label="Documents" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {tabValue === 0 && renderOverviewTab()}
        {tabValue === 1 && renderAITab()}
        {tabValue === 2 && renderDocumentsTab()}
      </Box>
    </Box>
  );
};

export default VehicleDetailsPage;
