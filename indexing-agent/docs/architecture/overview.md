# System Architecture & Flow

This document provides a detailed overview of the Generative Indexing system architecture and data flow.

## High-Level Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        A[HTTP Client]
        B[CLI Tool]
    end

    subgraph API["API Layer"]
        C[FastAPI Service]
        D[SSE Controller]
        E[Request Validator]
    end

    subgraph Core["Core Processing"]
        F[Indexing Pipeline]
        G[Schema Processor]
        H[File Processor]
    end

    subgraph AI["AI Processing"]
        I[Bedrock Service]
        J[Document Enhancer]
    end

    subgraph Storage["Storage Layer"]
        K[Elasticsearch]
        L[DynamoDB]
    end

    subgraph Monitor["Monitoring"]
        M[Logger]
        N[Progress Tracker]
    end

    A --> C
    B --> C
    C --> D
    C --> E
    E --> F
    F --> G
    F --> H
    F --> I
    I --> J
    F --> K
    F --> L
    F --> N
    N --> D
    F --> M
```

## Detailed Component Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Pipeline
    participant DynamoDB
    participant Bedrock
    participant Elasticsearch
    
    Client->>FastAPI: POST /triggerIndexingLive
    activate FastAPI
    FastAPI->>Client: SSE Connection Established
    
    FastAPI->>Pipeline: Initialize Pipeline
    activate Pipeline
    
    Pipeline->>DynamoDB: Fetch User Metadata
    activate DynamoDB
    DynamoDB-->>Pipeline: User Configuration
    deactivate DynamoDB
    
    Pipeline->>Pipeline: Read & Chunk Documents
    
    loop For each document chunk
        Pipeline->>Bedrock: Process Document
        activate Bedrock
        Bedrock-->>Pipeline: Enhanced Document
        deactivate Bedrock
        
        Pipeline->>Elasticsearch: Bulk Index Documents
        activate Elasticsearch
        Elasticsearch-->>Pipeline: Indexing Status
        deactivate Elasticsearch
        
        Pipeline->>FastAPI: Progress Update
        FastAPI->>Client: SSE Progress Event
    end
    
    Pipeline->>FastAPI: Completion Status
    deactivate Pipeline
    
    FastAPI->>Client: SSE Completion Event
    deactivate FastAPI
```

## Data Processing Pipeline

```mermaid
graph LR
    subgraph Input["Input Processing"]
        A[Raw Data] --> B[File Reader]
        B --> C[Chunker]
        C --> D[Validator]
    end

    subgraph Enhancement["AI Enhancement"]
        D --> E[Bedrock Client]
        E --> F[Content Processor]
        F --> G[Metadata Extractor]
    end

    subgraph Indexing["Search Indexing"]
        G --> H[Document Formatter]
        H --> I[Bulk Processor]
        I --> J[Index Manager]
    end

    subgraph Monitoring["Progress Tracking"]
        K[Status Tracker] --> L[SSE Emitter]
        L --> M[Client Updates]
    end

    D --> K
    G --> K
    J --> K
```

## System Components

### 1. Client Layer
- HTTP clients for API interaction
- CLI tools for batch processing
- SSE clients for real-time updates

### 2. API Layer
- FastAPI service handling requests
- Request validation and routing
- SSE controller for streaming updates
- Error handling and response formatting

### 3. Core Processing
- Document chunking and validation
- Schema processing and transformation
- Pipeline orchestration
- Error recovery and retry logic

### 4. AI Processing
- AWS Bedrock integration
- Document enhancement logic
- Content structuring
- Metadata extraction

### 5. Storage Layer
- Elasticsearch for document storage and search
- DynamoDB for user metadata and configurations
- Bulk operations handling
- Connection management

### 6. Monitoring
- Structured logging
- Progress tracking
- Status updates
- Error reporting

## Data Flow Description

1. **Input Stage**
   ```mermaid
   graph LR
       A[Input File] -->|Read| B[File Processor]
       B -->|Chunk| C[Document Chunks]
       C -->|Validate| D[Valid Documents]
   ```

2. **Processing Stage**
   ```mermaid
   graph LR
       A[Valid Documents] -->|Enhance| B[Bedrock AI]
       B -->|Extract| C[Metadata]
       B -->|Structure| D[Content]
       C --> E[Final Document]
       D --> E
   ```

3. **Storage Stage**
   ```mermaid
   graph LR
       A[Final Documents] -->|Batch| B[Bulk Processor]
       B -->|Index| C[Elasticsearch]
       B -->|Store Metadata| D[DynamoDB]
   ```

## Performance Considerations

### Parallel Processing
```mermaid
graph TB
    subgraph "Document Processing"
        P1[Processor 1]
        P2[Processor 2]
        P3[Processor 3]
    end
    
    subgraph "Bulk Indexing"
        B1[Batch 1]
        B2[Batch 2]
        B3[Batch 3]
    end
    
    D[Documents] --> P1 & P2 & P3
    P1 --> B1
    P2 --> B2
    P3 --> B3
    B1 & B2 & B3 --> E[Elasticsearch]
```

### Error Handling
```mermaid
graph TD
    A[Operation] -->|Try| B{Success?}
    B -->|No| C[Retry Logic]
    C -->|Attempt 1| A
    C -->|Max Retries| D[Error Handler]
    B -->|Yes| E[Next Step]
    D --> F[Error Response]
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        A[API Gateway]
        B[Authentication]
        C[Authorization]
        D[Data Encryption]
    end
    
    subgraph "Secure Storage"
        E[Encrypted Data]
        F[Access Logs]
        G[Audit Trail]
    end
    
    Client -->|HTTPS| A
    A --> B
    B --> C
    C --> D
    D --> E
    A --> F
    C --> G
```

This architecture ensures:
- Scalable processing
- Real-time updates
- Error resilience
- Secure operations
- Monitoring capabilities
- Data consistency