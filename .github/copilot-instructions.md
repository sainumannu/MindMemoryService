# PramaIA VectorStoreService - Copilot Instructions

## System Overview

This is a FastAPI-based microservice that provides centralized vector database management using ChromaDB with SQLite metadata storage. The service acts as a bridge between filesystem documents and semantic search capabilities.

## Architecture Patterns

### Hybrid Database Strategy
- **ChromaDB**: Vector embeddings for semantic search (`app/core/vectordb_manager.py`)
- **SQLite**: Document metadata and structured data (`app/utils/document_database.py`)  
- **HybridDocumentManager**: Coordinates operations between both databases (`app/utils/hybrid_document_manager.py`)

Always update both databases in coordinated operations. The hybrid manager handles failure scenarios and maintains consistency.

### Singleton Pattern Usage
- **VectorDBManager**: Single ChromaDB client instance with fallback to in-memory mode
- **FileWatcher**: Global file monitoring with change handlers (`app/utils/file_watcher.py`)

## Key Development Workflows

### Service Startup
```powershell
python main.py  # Development mode with auto-reload
```

### Database Initialization/Cleanup
```powershell
python scripts\init_vectorstore.py    # Initialize and scan for documents
python scripts\clean_vectorstore.py   # Reset/cleanup for testing
python scripts\migrate_to_sqlite.py   # Database migration
```

### Testing
```powershell
python tests\test_get_document.py  # Specific API tests
```

## API Gateway Pattern

The service uses a multi-layered routing approach in `app/api/__init__.py`:
- **Primary routes**: `/vectorstore/*`, `/documents/*` 
- **Compatibility routes**: `/collections/*` redirects to `/vectorstore/collections`
- **Frontend gateway**: `/api/database-management/*` maps to internal endpoints
- **Legacy support**: `/documents/status` combines documents + stats

## File System Integration

### File Watcher (`app/utils/file_watcher.py`)
- Monitors filesystem changes with detailed logging
- Uses `FileChange` dataclass with `ChangeType` enum
- Integrates with reconciliation system for automatic sync

### Document Processing
- PDF scanning in `scripts/init_vectorstore.py`
- Recursive directory processing with metadata extraction
- Batch operations preferred over individual file handling

## Configuration Management

### Multi-source Configuration
- **Environment**: `.env` file for development
- **JSON Config**: `config/vectorstore_config.json` for runtime settings
- **Dynamic API**: `/api/configuration` endpoints for live updates

### ChromaDB Setup
Uses persistent local mode with fallback strategy:
```python
# Persistent mode preferred
client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
# Fallback to in-memory if persistent fails
client = chromadb.Client()  
```

## Error Handling Patterns

### ChromaDB Connection
Always implement fallback initialization pattern seen in `VectorDBManager._init_client()`:
1. Try persistent client with conservative settings
2. Fallback to in-memory client on failure  
3. Log detailed error information for troubleshooting

### API Error Responses
Use FastAPI's HTTPException with specific status codes and detailed messages for client integration.

## Logging Strategy

### Structured Logging
- **Simple Logger**: `app/utils/logger_simple.py` for basic operations
- **Detailed Logger**: `app/utils/logger.py` for complex workflows
- **File-specific**: Each major component maintains its own logger namespace

### Log Integration
Service integrates with PramaIA-LogService when available (see `setup.py` for client installation).

## Dependencies and External Integration

### Critical Dependencies
- **ChromaDB 0.4.24**: Specific version for Python 3.13 compatibility
- **FastAPI**: Core web framework with CORS middleware
- **SQLAlchemy**: Database ORM with Alembic migrations

### PramaIA Ecosystem
- **LogService**: Optional centralized logging (installed from `../PramaIA-LogService/clients/python`)
- **Frontend**: React components in `app/frontend/` consume service APIs
- **PDK Integration**: See `docs/INTEGRATION_GUIDE.md` for client usage patterns

## Common Gotchas

1. **ChromaDB Collection Names**: Use `CHROMA_COLLECTION_NAME = "prama_documents"` constant
2. **Data Directory**: Always use `data/` subdirectory with proper path construction
3. **Batch Operations**: Prefer batch document operations over individual calls for performance
4. **Router Order**: API router inclusion order matters for route precedence in `app/api/__init__.py`
5. **File Watching**: File changes trigger automatic reconciliation - consider performance impact

## Testing Approach

- Service-level tests in `tests/` directory with actual HTTP calls
- Start service on port 8090 before running tests
- Use `test_get_document.py` pattern for new endpoint tests