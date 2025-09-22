# Storage Interfaces (v1.2)

## Overview

MemoryOS implements a multi-layered storage architecture with ACID guarantees, conflict-free replication, and comprehensive privacy controls. All storage operations are coordinated through the Enhanced Unit of Work pattern with performance monitoring, transaction receipts, and comprehensive error handling.

**Enhanced in v1.2:**
- Connection pooling and WAL mode optimization
- Performance monitoring and analytics
- Comprehensive transaction receipts with cryptographic integrity
- Enhanced error handling and recovery mechanisms
- Migration system with version control and rollback capabilities

## Core Interfaces

### Enhanced UnitOfWork (v1.1)
- **File**: `storage/unit_of_work.py`
- **Purpose**: Coordinates atomic operations across multiple stores with enhanced capabilities
- **New Features**:
  - **Performance Monitoring**: Execution time tracking, metrics collection
  - **Transaction Receipts**: Cryptographic verification and audit trails
  - **Error Recovery**: Comprehensive error handling with retry logic
  - **Contract Compliance**: Full validation against storage contracts
  - **Context Tracking**: Space, actor, device, and correlation ID tracking
- **Invariants**:
  - Atomic commit across stores (episodic/semantic/fts/vector/receipts)
  - Idempotent operations with receipt hashes
  - Emits `ACTION_EXECUTED` receipts on successful commits
  - Rollback on any store failure with detailed error tracking
  - Performance metrics collection for all operations

### Enhanced SQLite Manager (v1.2)
- **File**: `storage/sqlite_enhanced.py`
- **Purpose**: High-performance SQLite backend with connection pooling and optimizations
- **New Features**:
  - **Connection Pooling**: Configurable min/max connections with timeout management
  - **WAL Mode**: Write-Ahead Logging for improved concurrency
  - **Vacuum Management**: Automatic and manual vacuum operations with tracking
  - **Performance Monitoring**: Query timing, cache hit rates, I/O metrics
  - **Health Checks**: Database integrity verification and diagnostics
- **Configuration**:
  - Pool sizes: 2-8 connections default, configurable per database
  - Timeout: 30 seconds default for connection acquisition
  - Cache: 64MB cache with memory temp storage
  - MMAP: 256MB memory mapping for large databases

### Migration System (v1.0)
- **File**: `storage/migration_system.py`
- **Purpose**: Database schema evolution with version control and rollback capabilities
- **Features**:
  - **Semantic Versioning**: Full version comparison and breaking change detection
  - **Transaction Safety**: All migrations run in transactions with automatic rollback
  - **Contract Integration**: Discovers migrations from `contracts/storage/migrations/`
  - **Rollback Support**: Full rollback capabilities with data preservation
  - **Integrity Validation**: Checksum verification of applied migrations
  - **History Tracking**: Complete audit trail of all migration operations
- **Guarantees**:
  - Atomic migration application (all-or-nothing)
  - Checksum verification for migration integrity
  - Complete rollback capability to any previous version
  - Contract-driven schema evolution

### Enhanced Repository Pattern

All storage implementations follow the enhanced repository pattern with consistent interfaces and new capabilities:

#### Common Enhancements (v1.1+):
- **Performance Metrics**: Automatic collection of operation timing and throughput
- **Error Recovery**: Retry logic with exponential backoff for transient failures
- **Context Awareness**: Full integration with space, actor, and device context
- **Contract Validation**: Runtime validation against storage contracts
- **Receipt Generation**: Cryptographic receipts for all write operations

#### EpisodicStore
- **File**: `storage/episodic_store.py`
- **Purpose**: Temporal sequence storage and retrieval
- **Features**: Time-ordered events, sequence grouping, temporal queries
- **Schema**: Event streams with timestamps and sequence IDs

#### SemanticStore
- **File**: `storage/semantic_store.py`
- **Purpose**: Knowledge graph and structured data storage
- **Features**: Entity-relationship modeling, semantic queries, graph traversal
- **Schema**: RDF-like triples with semantic annotations

#### FTSStore (Full-Text Search)
- **File**: `storage/fts_store.py`
- **Purpose**: Text content indexing and search
- **Features**: Stemming, ranking, phrase queries, faceted search
- **Schema**: Inverted index with TF-IDF scoring

#### VectorStore
- **File**: `storage/vector_store.py`
- **Purpose**: Embedding-based similarity search
- **Features**: High-dimensional vectors, ANN search, similarity ranking
- **Schema**: Dense vectors with metadata and similarity metrics

#### EmbeddingsStore
- **File**: `storage/embeddings_store.py`
- **Purpose**: Embedding model management and caching
- **Features**: Model versioning, embedding lifecycle, cache invalidation
- **Schema**: Model metadata with embedding tensors

#### ReceiptsStore
- **File**: `storage/receipts_store.py`
- **Purpose**: Audit trail and operation receipts
- **Features**: Immutable logging, integrity verification, compliance tracking
- **Schema**: Cryptographic receipts with operation metadata

#### CRDTStore
- **File**: `storage/crdt_store.py`
- **Purpose**: Conflict-free replicated data types for P2P sync
- **Features**: Merge semantics, causal ordering, tombstone handling
- **Schema**: CRDT state with vector clocks and merge history

## Additional Stores

### Specialized Storage Components

- **WorkspaceStore**: `storage/workspace_store.py` - Global workspace state
- **MetacogStore**: `storage/metacog_store.py` - Metacognitive monitoring data
- **ProspectiveStore**: `storage/prospective_store.py` - Future-oriented planning
- **DrivesStore**: `storage/drives_store.py` - Motivational state tracking
- **ImaginationStore**: `storage/imagination_store.py` - Simulation results
- **AffectStore**: `storage/affect_store.py` - Emotional state history
- **HippocampusStore**: `storage/hippocampus_store.py` - Memory consolidation
- **PrivacyStore**: `storage/privacy_store.py` - Privacy preferences and tombstones
- **MLStore**: `storage/ml_store.py` - Model artifacts and metrics
- **RegistriesStore**: `storage/registries_store.py` - Tool and agent registrations

## Consistency Model

### Transaction Guarantees
- **Atomicity**: All-or-nothing commits across stores
- **Consistency**: Invariant preservation during transactions
- **Isolation**: Snapshot reads under Unit of Work
- **Durability**: WAL and fsync guarantees

### CRDT Semantics
- **Monotonic Merge**: CRDT operations are commutative and associative
- **Tombstone Precedence**: Deletions take priority in conflict resolution
- **Causal Ordering**: Vector clocks maintain causal relationships
- **Eventual Consistency**: All replicas converge to same state

## Security & Privacy

### Multi-Level Security (MLS)
- **Memory Spaces**: Hierarchical security domains
  - `personal:*` - Individual user data
  - `selective:*` - Selective sharing (e.g., father_son)
  - `shared:household` - Family-level sharing
  - `extended:grandparents` - Extended family access
- **Band-Based Access**: GREEN/AMBER/RED/BLACK security levels
- **Compartmentalization**: Cryptographic isolation between spaces

### Encryption
- **At-Rest**: AES-256-GCM for all stored data
- **In-Transit**: TLS 1.3 for synchronization
- **Key Management**: Per-space encryption keys with key ratcheting
- **Forward Secrecy**: Regular key rotation and secure deletion

### Privacy Controls
- **Data Minimization**: Automatic PII detection and redaction
- **Retention Policies**: Configurable data lifecycle management
- **Tombstones**: Secure deletion with audit trails
- **GDPR Compliance**: Right to be forgotten implementation

## Performance Characteristics (Enhanced v1.2)

### Storage Engine
- **SQLite Backend**: ACID guarantees with WAL mode for improved concurrency
- **Connection Pooling**: 2-8 connections per database with 30s timeout
- **Optimizations**: 64MB cache, memory temp storage, 256MB MMAP
- **Indexing**: Multi-column indexes for common query patterns with automatic optimization
- **Vacuum Management**: Automatic incremental vacuum with space reclamation tracking

### Enhanced Performance Targets (v1.2)
- **Unit of Work Operations**: p95 ≤ 60ms (improved from 100ms)
- **Connection Acquisition**: p95 ≤ 50ms from pool
- **Query Performance**:
  - Simple queries: p95 ≤ 30ms (improved from 50ms)
  - Complex aggregations: p95 ≤ 300ms (improved from 500ms)
- **Migration Operations**: p95 ≤ 5 minutes for databases < 1GB
- **Health Check Suite**: p95 ≤ 500ms for complete validation

### Caching Strategy
- **Write-Through**: Immediate persistence with async processing
- **Read Caches**: LRU caches for frequently accessed data with 70%+ hit rate
- **Embedding Cache**: Vector similarity results with TTL-based expiration
- **Query Cache**: Compiled query plans and result sets
- **Connection Pool**: Persistent connections with lifecycle management

### Monitoring & Analytics
- **Real-time Metrics**: Query timing, cache hit rates, pool utilization
- **Performance Trends**: Historical analysis with 30-day retention
- **Health Dashboards**: Database integrity, space usage, vacuum efficiency
- **Alert Thresholds**: Configurable performance degradation detection

## Implementation Notes

### File Organization
```
storage/
├── base_store.py           # Abstract base classes
├── interfaces.py           # Interface definitions
├── unit_of_work.py        # Transaction coordinator
├── sqlite_util.py         # SQLite utilities
├── tiered_memory_service.py # Memory hierarchy management
├── pattern_detector.py    # Data pattern recognition
└── schema/               # Database schemas
    └── tombstones.sql    # Deletion tracking schema
```

### Extension Points
- **Custom Stores**: Implement `BaseStore` interface
- **Storage Adapters**: Plugin architecture for external storage
- **Compression**: Configurable compression algorithms
- **Replication**: Multi-master sync with conflict resolution

## Error Handling

### Failure Modes
- **Storage Corruption**: Automatic repair and fallback
- **Disk Full**: Graceful degradation and cleanup
- **Concurrent Access**: Lock-free optimistic concurrency
- **Network Partitions**: Offline-first with eventual sync

### Recovery Procedures
- **Checkpointing**: Regular consistency checkpoints
- **Rollback**: Transaction rollback on failure
- **Repair**: Automatic corruption detection and repair
- **Backup**: Incremental backup with compression

## Monitoring & Observability

### Metrics
- **Performance**: Query latency, throughput, cache hit rates
- **Storage**: Disk usage, compaction frequency, index sizes
- **Errors**: Failure rates, recovery times, corruption events
- **Security**: Access violations, encryption failures, audit logs

### Tracing
- **Operation Tracing**: End-to-end request tracking
- **Query Plans**: SQL execution plan analysis
- **Cache Analytics**: Hit/miss patterns and optimization
- **Sync Monitoring**: Replication lag and conflict resolution
