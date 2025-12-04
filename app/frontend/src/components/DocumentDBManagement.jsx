import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  CircularProgress,
  Divider,
  Alert,
  Tabs,
  Tab,
  LinearProgress
} from '@mui/material';
import {
  Backup as BackupIcon,
  Restore as RestoreIcon,
  DeleteSweep as CleanupIcon,
  Storage as StorageIcon,
  Speed as PerformanceIcon
} from '@mui/icons-material';
import axios from 'axios';

// Componente per la gestione del database dei documenti
function DocumentDBManagement() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dbStats, setDbStats] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [backupInProgress, setBackupInProgress] = useState(false);
  const [lastBackup, setLastBackup] = useState(null);
  const [optimizeInProgress, setOptimizeInProgress] = useState(false);
  const [message, setMessage] = useState(null);

  // Carica le statistiche del database
  const loadDatabaseStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/v1/admin/database/stats');
      setDbStats(response.data);
    } catch (err) {
      console.error('Errore nel caricamento delle statistiche del database documenti:', err);
      setError('Impossibile caricare le statistiche del database documenti');
    } finally {
      setLoading(false);
    }
  };

  // Crea un backup del database
  const createBackup = async () => {
    setBackupInProgress(true);
    setMessage(null);
    
    try {
      const response = await axios.post('/api/v1/admin/database/backup');
      setLastBackup(response.data.backupPath);
      setMessage({
        type: 'success',
        text: 'Backup del database documenti creato con successo'
      });
      
      // Ricarica le statistiche
      loadDatabaseStats();
    } catch (err) {
      console.error('Errore nella creazione del backup:', err);
      setMessage({
        type: 'error',
        text: 'Errore nella creazione del backup del database documenti'
      });
    } finally {
      setBackupInProgress(false);
    }
  };

  // Ottimizza il database
  const optimizeDatabase = async () => {
    setOptimizeInProgress(true);
    setMessage(null);
    
    try {
      const response = await axios.post('/api/v1/admin/database/optimize');
      
      setMessage({
        type: 'success',
        text: `Database documenti ottimizzato con successo. Spazio recuperato: ${response.data.reductionPercentage.toFixed(2)}%`
      });
      
      // Ricarica le statistiche
      loadDatabaseStats();
    } catch (err) {
      console.error('Errore nell\'ottimizzazione del database:', err);
      setMessage({
        type: 'error',
        text: 'Errore nell\'ottimizzazione del database documenti'
      });
    } finally {
      setOptimizeInProgress(false);
    }
  };

  // Gestisce il cambio di tab
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Carica le statistiche all'avvio
  useEffect(() => {
    loadDatabaseStats();
    
    // Carica le informazioni sull'ultimo backup
    const fetchLastBackup = async () => {
      try {
        const response = await axios.get('/api/v1/admin/database/backup/latest');
        if (response.data && response.data.path) {
          setLastBackup(response.data.path);
        }
      } catch (err) {
        console.error('Errore nel caricamento delle informazioni sul backup:', err);
      }
    };
    
    fetchLastBackup();
  }, []);

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Gestione Database Documenti
      </Typography>
      
      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 2 }}>
        Monitora e gestisci il database dei metadati dei documenti
      </Typography>
      
      {message && (
        <Alert 
          severity={message.type} 
          sx={{ mb: 2 }}
          onClose={() => setMessage(null)}
        >
          {message.text}
        </Alert>
      )}
      
      <Box sx={{ mb: 2 }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange} 
          aria-label="document db management tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Panoramica" />
          <Tab label="Documenti" />
          <Tab label="Backup e Ripristino" />
          <Tab label="Prestazioni" />
        </Tabs>
      </Box>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : (
        <Box>
          {/* Tab Panoramica */}
          {activeTab === 0 && dbStats && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" component="h3" gutterBottom>
                      <StorageIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Database Documenti
                    </Typography>
                    <Typography variant="h3" component="div" color="primary">
                      {dbStats.documents || 0}
                    </Typography>
                    <Typography color="text.secondary">
                      documenti indicizzati
                    </Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Dimensione: {dbStats.size} KB
                      </Typography>
                    </Box>
                    <Box sx={{ mt: 1 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={Math.min(dbStats.usage || 0, 100)} 
                        sx={{ height: 8, borderRadius: 2 }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        Utilizzo spazio: {dbStats.usage || 0}%
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" component="h3" gutterBottom>
                      <PerformanceIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Stato
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: 'success.main',
                          mr: 1
                        }}
                      />
                      <Typography variant="body1">
                        Operativo
                      </Typography>
                    </Box>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        SQLite versione: {dbStats.sqliteVersion || '3.x'}
                      </Typography>
                      <Typography variant="body2">
                        Ultimo ottimizzazione: {dbStats.lastOptimized || 'Mai'}
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" component="h3" gutterBottom>
                      Operazioni Rapide
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 2 }}>
                      <Button 
                        variant="outlined" 
                        startIcon={<BackupIcon />}
                        onClick={createBackup}
                        disabled={backupInProgress}
                      >
                        {backupInProgress ? 'Backup in corso...' : 'Crea Backup'}
                      </Button>
                      
                      <Button 
                        variant="outlined" 
                        startIcon={<CleanupIcon />}
                        onClick={optimizeDatabase}
                        disabled={optimizeInProgress}
                      >
                        {optimizeInProgress ? 'Ottimizzazione...' : 'Ottimizza DB'}
                      </Button>
                      
                      <Button 
                        variant="outlined" 
                        color="primary"
                        onClick={loadDatabaseStats}
                      >
                        Aggiorna
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
          
          {/* Tab Documenti */}
          {activeTab === 1 && dbStats && (
            <Card>
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  Documenti Indicizzati
                </Typography>
                <Typography variant="body1" paragraph>
                  Il database contiene attualmente {dbStats.documents || 0} documenti.
                </Typography>
                
                <Box sx={{ mt: 2 }}>
                  <Alert severity="info">
                    Per visualizzare e gestire i documenti, utilizza la sezione "Documenti indicizzati"
                  </Alert>
                </Box>
              </CardContent>
            </Card>
          )}
          
          {/* Tab Backup e Ripristino */}
          {activeTab === 2 && (
            <Card>
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  Backup e Ripristino
                </Typography>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Ultimo backup
                  </Typography>
                  <Typography variant="body1">
                    {lastBackup ? lastBackup : 'Nessun backup disponibile'}
                  </Typography>
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 2 }}>
                  <Button 
                    variant="contained" 
                    color="primary"
                    startIcon={<BackupIcon />}
                    onClick={createBackup}
                    disabled={backupInProgress}
                  >
                    {backupInProgress ? 'Backup in corso...' : 'Crea Nuovo Backup'}
                  </Button>
                  
                  <Button 
                    variant="outlined" 
                    startIcon={<RestoreIcon />}
                    disabled={!lastBackup}
                  >
                    Ripristina da Backup
                  </Button>
                </Box>
              </CardContent>
            </Card>
          )}
          
          {/* Tab Prestazioni */}
          {activeTab === 3 && dbStats && (
            <Card>
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  Prestazioni Database
                </Typography>
                
                <Alert severity="info" sx={{ mb: 3 }}>
                  L'ottimizzazione del database può migliorare significativamente le prestazioni, specialmente dopo molte operazioni di inserimento o cancellazione.
                </Alert>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Stato attuale
                  </Typography>
                  <Typography variant="body1">
                    Dimensione: {dbStats.size} KB
                  </Typography>
                  <Typography variant="body1">
                    Frammentazione stimata: {dbStats.fragmentation || 'N/A'}%
                  </Typography>
                </Box>
                
                <Box sx={{ mt: 2 }}>
                  <Button 
                    variant="contained" 
                    color="primary"
                    startIcon={<CleanupIcon />}
                    onClick={optimizeDatabase}
                    disabled={optimizeInProgress}
                  >
                    {optimizeInProgress ? 'Ottimizzazione...' : 'Ottimizza Database (VACUUM)'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Box>
  );
}

export default DocumentDBManagement;
