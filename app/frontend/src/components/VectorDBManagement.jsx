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
  LinearProgress,
  Chip
} from '@mui/material';
import {
  Storage as StorageIcon,
  Speed as PerformanceIcon,
  DeleteSweep as CleanupIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import axios from 'axios';

// Componente per la gestione del database vettoriale (ChromaDB)
function VectorDBManagement() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dbStats, setDbStats] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [resetInProgress, setResetInProgress] = useState(false);
  const [message, setMessage] = useState(null);
  const [collections, setCollections] = useState([]);

  // Carica le statistiche del database vettoriale
  const loadVectorStats = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Ottieni statistiche generali
      const statsResponse = await axios.get('/api/v1/vectorstore/stats');
      
      // Ottieni elenco delle collezioni
      const collectionsResponse = await axios.get('/api/v1/collections');
      
      setDbStats(statsResponse.data);
      setCollections(collectionsResponse.data || []);
    } catch (err) {
      console.error('Errore nel caricamento delle statistiche del database vettoriale:', err);
      setError('Impossibile caricare le statistiche del database vettoriale');
    } finally {
      setLoading(false);
    }
  };

  // Reset completo del database vettoriale
  const resetVectorDB = async () => {
    // Conferma con l'utente prima di eseguire
    if (!window.confirm('Sei sicuro di voler resettare il database vettoriale? Questa operazione è irreversibile.')) {
      return;
    }
    
    setResetInProgress(true);
    setMessage(null);
    
    try {
      const response = await axios.post('/api/v1/vectorstore/reset');
      
      setMessage({
        type: 'success',
        text: 'Database vettoriale resettato con successo'
      });
      
      // Ricarica le statistiche
      loadVectorStats();
    } catch (err) {
      console.error('Errore nel reset del database vettoriale:', err);
      setMessage({
        type: 'error',
        text: 'Errore nel reset del database vettoriale'
      });
    } finally {
      setResetInProgress(false);
    }
  };

  // Gestisce il cambio di tab
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Carica le statistiche all'avvio
  useEffect(() => {
    loadVectorStats();
  }, []);

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Gestione Database Vettoriale
      </Typography>
      
      <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 2 }}>
        Monitora e gestisci il database vettoriale (ChromaDB)
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
          aria-label="vector db management tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Panoramica" />
          <Tab label="Collezioni" />
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
                      Stato ChromaDB
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: dbStats.status === 'healthy' ? 'success.main' : 'error.main',
                          mr: 1
                        }}
                      />
                      <Typography variant="body1">
                        {dbStats.status === 'healthy' ? 'Operativo' : 'Problemi rilevati'}
                      </Typography>
                    </Box>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        Versione ChromaDB: {dbStats.version || 'N/A'}
                      </Typography>
                      <Typography variant="body2">
                        Modalità: {dbStats.persistenceMode || 'Locale'}
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
                      Collezioni
                    </Typography>
                    <Typography variant="h3" component="div" color="primary">
                      {collections.length}
                    </Typography>
                    <Typography color="text.secondary">
                      collezioni attive
                    </Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        Totale embedding: {dbStats.totalEmbeddings || 'N/A'}
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
                        color="error"
                        startIcon={<CleanupIcon />}
                        onClick={resetVectorDB}
                        disabled={resetInProgress}
                      >
                        {resetInProgress ? 'Reset in corso...' : 'Reset Vector Store'}
                      </Button>
                      
                      <Button 
                        variant="outlined" 
                        color="primary"
                        startIcon={<RefreshIcon />}
                        onClick={loadVectorStats}
                      >
                        Aggiorna
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
          
          {/* Tab Collezioni */}
          {activeTab === 1 && (
            <Card>
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  Collezioni
                </Typography>
                
                {collections.length === 0 ? (
                  <Alert severity="info">
                    Nessuna collezione presente nel database vettoriale.
                  </Alert>
                ) : (
                  <Box sx={{ mt: 2 }}>
                    <Grid container spacing={2}>
                      {collections.map((collection) => (
                        <Grid item xs={12} key={collection.name}>
                          <Card variant="outlined" sx={{ p: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Typography variant="subtitle1" fontWeight="bold">
                                {collection.name}
                              </Typography>
                              <Chip 
                                label={`${collection.count || 0} embeddings`} 
                                color="primary" 
                                size="small" 
                              />
                            </Box>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                              ID: {collection.id}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Metadata: {JSON.stringify(collection.metadata || {})}
                            </Typography>
                          </Card>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}
          
          {/* Tab Prestazioni */}
          {activeTab === 2 && dbStats && (
            <Card>
              <CardContent>
                <Typography variant="h6" component="h3" gutterBottom>
                  Prestazioni Database Vettoriale
                </Typography>
                
                <Alert severity="info" sx={{ mb: 3 }}>
                  Le prestazioni del database vettoriale dipendono da vari fattori come la dimensione degli embedding e il numero di documenti indicizzati.
                </Alert>
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Stato attuale
                  </Typography>
                  <Typography variant="body1">
                    Dimensione stimata: {dbStats.estimatedSize || 'N/A'} MB
                  </Typography>
                  <Typography variant="body1">
                    Tempo medio di query: {dbStats.avgQueryTime || 'N/A'} ms
                  </Typography>
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                <Box sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Consigli per le prestazioni
                  </Typography>
                  <Typography variant="body2" paragraph>
                    • Per migliorare le prestazioni, considera la creazione di indici specifici per le query più frequenti.
                  </Typography>
                  <Typography variant="body2" paragraph>
                    • Se il database è molto grande, considera l'utilizzo di una installazione separata di ChromaDB.
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Box>
  );
}

export default VectorDBManagement;
