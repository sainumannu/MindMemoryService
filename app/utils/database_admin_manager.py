from .document_manager import DocumentManager

class DatabaseAdminManager(DocumentManager):
    def reset_database(self):
        return self.reset_all_data()
    
    def get_health_status(self):
        return self.health_check()
    
    def get_db_statistics(self):
        return self.get_statistics()

# Alias per compatibilita
ExtendedMetadataStoreManager = DatabaseAdminManager