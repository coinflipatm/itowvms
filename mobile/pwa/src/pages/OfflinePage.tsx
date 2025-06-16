import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
} from '@mui/material';
import {
  CloudOff as OfflineIcon,
  Sync as SyncIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

const OfflinePage: React.FC = () => {
  const pendingActions = JSON.parse(localStorage.getItem('pendingActions') || '[]');

  const handleRetryConnection = () => {
    window.location.reload();
  };

  return (
    <Box 
      sx={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        p: 2,
        bgcolor: 'grey.100'
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent sx={{ textAlign: 'center', p: 4 }}>
          <OfflineIcon 
            sx={{ 
              fontSize: 80, 
              color: 'warning.main', 
              mb: 2 
            }} 
          />
          
          <Typography variant="h5" gutterBottom>
            You're Offline
          </Typography>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            You can continue working in offline mode. Your changes will be synced when you're back online.
          </Typography>

          {pendingActions.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Chip
                icon={<SyncIcon />}
                label={`${pendingActions.length} pending actions`}
                color="warning"
                variant="outlined"
              />
            </Box>
          )}

          <Button
            variant="contained"
            onClick={handleRetryConnection}
            sx={{ mb: 2, width: '100%' }}
          >
            Retry Connection
          </Button>

          {pendingActions.length > 0 && (
            <Card variant="outlined" sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Pending Actions
                </Typography>
                <List dense>
                  {pendingActions.slice(0, 5).map((action: any, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <WarningIcon color="warning" />
                      </ListItemIcon>
                      <ListItemText
                        primary={action.type}
                        secondary={new Date(action.timestamp).toLocaleString()}
                      />
                    </ListItem>
                  ))}
                </List>
                {pendingActions.length > 5 && (
                  <Typography variant="caption" color="text.secondary">
                    +{pendingActions.length - 5} more actions
                  </Typography>
                )}
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default OfflinePage;
