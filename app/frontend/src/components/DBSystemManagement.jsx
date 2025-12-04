import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Memory as MemoryIcon,
  Extension as PluginIcon,
  Assessment as StatisticsIcon,
  DynamicFeed as SystemIcon
} from '@mui/icons-material';

import DocumentDBManagement from './DocumentDBManagement';
import VectorDBManagement from './VectorDBManagement';

// Componente principale per la gestione di tutti i database del sistema
function DBSystemManagement() {
  const [activeTab, setActiveTab] = useState(0);
  
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  
  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Gestione Database Sistema
      </Typography>
      
      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 3 }}>
        Monitora e gestisci tutti i database e archivi dati del sistema
      </Typography>
      
      <Paper sx={{ mb: 3 }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange} 
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab 
            label="Panoramica" 
            icon={<DatabaseIcon />} 
            iconPosition="start" 
          />
          <Tab 
            label="Database Documenti" 
            icon={<SystemIcon />} 
            iconPosition="start" 
          />
          <Tab 
            label="Database Vettoriale" 
            icon={<MemoryIcon />} 
            iconPosition="start" 
          />
        </Tabs>
      </Paper>
      
      {/* Tab Panoramica */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h5" component="h2" gutterBottom>
                  Panoramica Database Sistema
                </Typography>
                
                <Alert severity="info" sx={{ mb: 3 }}>
                  Il sistema utilizza diversi database specializzati per gestire diversi tipi di dati.
                  Seleziona un database specifico dalle schede sopra per gestirlo.
                </Alert>
                
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <SystemIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Database Documenti (SQLite)" 
                      secondary="Archivia i metadati e le informazioni sui documenti elaborati dal sistema" 
                    />
                    <Button 
                      variant="outlined" 
                      size="small"
                      onClick={() => setActiveTab(1)}
                    >
                      Gestisci
                    </Button>
                  </ListItem>
                  
                  <Divider variant="inset" component="li" />
                  
                  <ListItem>
                    <ListItemIcon>
                      <MemoryIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary="Database Vettoriale (ChromaDB)" 
                      secondary="Archivia gli embedding e gestisce la ricerca semantica dei documenti" 
                    />
                    <Button 
                      variant="outlined" 
                      size="small"
                      onClick={() => setActiveTab(2)}
                    >
                      Gestisci
                    </Button>
                  </ListItem>
                </List>
                
                <Box sx={{ mt: 4, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Buone Pratiche di Gestione
                  </Typography>
                  
                  <Typography variant="body2" paragraph>
                    • <strong>Backup regolari</strong>: Esegui backup periodici di entrambi i database per prevenire la perdita di dati.
                  </Typography>
                  
                  <Typography variant="body2" paragraph>
                    • <strong>Ottimizzazione</strong>: Utilizza le funzionalità di ottimizzazione per mantenere le prestazioni ottimali.
                  </Typography>
                  
                  <Typography variant="body2" paragraph>
                    • <strong>Monitoraggio</strong>: Controlla regolarmente lo stato dei database e la loro dimensione.
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
      
      {/* Tab Database Documenti */}
      {activeTab === 1 && (
        <DocumentDBManagement />
      )}
      
      {/* Tab Database Vettoriale */}
      {activeTab === 2 && (
        <VectorDBManagement />
      )}
    </Box>
  );
}

export default DBSystemManagement;
