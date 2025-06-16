import React, { useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  IconButton,
} from '@mui/material';
import {
  DirectionsCar as CarIcon,
  Warning as WarningIcon,
  AttachMoney as MoneyIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
  Psychology as AIIcon,
} from '@mui/icons-material';

import { RootState } from '../store';
import { apiClient } from '../api/client';

interface DashboardStats {
  totalVehicles: number;
  urgentItems: number;
  totalValue: number;
  pendingDispositions: number;
  recentActivity: Array<{
    id: string;
    message: string;
    time: string;
    type: 'vehicle' | 'workflow' | 'ai';
  }>;
  aiInsights: Array<{
    id: string;
    type: string;
    message: string;
    confidence: number;
  }>;
}

const DashboardPage: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth);
  const { status } = useSelector((state: RootState) => state.sync);
  
  const [stats, setStats] = React.useState<DashboardStats>({
    totalVehicles: 0,
    urgentItems: 0,
    totalValue: 0,
    pendingDispositions: 0,
    recentActivity: [],
    aiInsights: [],
  });
  const [loading, setLoading] = React.useState(true);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getDashboardData();
      
      if (response.success && response.data) {
        const data = response.data;
        setStats({
          totalVehicles: data.vehicleStats.total,
          urgentItems: data.urgentItems.length,
          totalValue: data.vehicleStats.totalValue,
          pendingDispositions: data.vehicleStats.byStatus['pending_disposition'] || 0,
          recentActivity: data.recentVehicles.slice(0, 5).map((v: any) => ({
            id: v.id.toString(),
            message: `${v.make} ${v.model} - ${v.status}`,
            time: v.updated_at || v.created_at || '',
            type: 'vehicle' as const,
          })),
          aiInsights: data.aiInsights.slice(0, 3).map((insight: any) => ({
            id: insight.id,
            type: insight.type,
            message: insight.explanation,
            confidence: insight.confidence,
          })),
        });
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    return `${Math.floor(diffInHours / 24)}d ago`;
  };

  return (
    <Box sx={{ p: 2 }}>
      {/* Welcome Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          Welcome back, {user?.username}!
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {new Date().toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
          })}
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CarIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  {stats.totalVehicles}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Total Vehicles
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <WarningIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  {stats.urgentItems}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Urgent Items
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <MoneyIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  {formatCurrency(stats.totalValue)}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Total Value
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <ScheduleIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="h6" component="div">
                  {stats.pendingDispositions}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Pending Dispositions
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* AI Insights */}
      {stats.aiInsights.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <AIIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">AI Insights</Typography>
            </Box>
            
            {stats.aiInsights.map((insight) => (
              <Box key={insight.id} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Chip 
                    size="small" 
                    label={insight.type} 
                    color="primary" 
                    sx={{ mr: 1 }} 
                  />
                  <Typography variant="body2" color="text.secondary">
                    {Math.round(insight.confidence * 100)}% confidence
                  </Typography>
                </Box>
                <Typography variant="body2">
                  {insight.message}
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={insight.confidence * 100}
                  sx={{ mt: 1, height: 4, borderRadius: 2 }}
                />
              </Box>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent Activity */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Recent Activity</Typography>
            <IconButton onClick={loadDashboardData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Box>
          
          {loading ? (
            <LinearProgress />
          ) : (
            <List disablePadding>
              {stats.recentActivity.map((activity, index) => (
                <ListItem key={activity.id} divider={index < stats.recentActivity.length - 1}>
                  <ListItemIcon>
                    <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                      <CarIcon sx={{ fontSize: 18 }} />
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary={activity.message}
                    secondary={formatTimeAgo(activity.time)}
                  />
                </ListItem>
              ))}
              
              {stats.recentActivity.length === 0 && (
                <ListItem>
                  <ListItemText
                    primary="No recent activity"
                    secondary="New updates will appear here"
                  />
                </ListItem>
              )}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Sync Status */}
      {status.pendingActions > 0 && (
        <Card sx={{ mt: 2, bgcolor: 'warning.light' }}>
          <CardContent>
            <Typography variant="body2" color="warning.contrastText">
              {status.pendingActions} actions pending sync
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default DashboardPage;
