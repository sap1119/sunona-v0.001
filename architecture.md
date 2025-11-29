# Backend Architecture - Complete Setup & Flow

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Entry Point"
        Server[local_server.py<br/>FastAPI Application]
    end
    
    subgraph "API Layer - /api/v1/"
        APIRouter[API Router<br/>__init__.py]
        AuthAPI[auth.py<br/>Authentication Routes]
        WalletAPI[wallet.py<br/>Wallet Routes]
        CallsAPI[calls.py<br/>Call Routes]
        AgentsAPI[agents.py<br/>Agent Routes]
        PaymentsAPI[payments.py<br/>Payment Routes]
        AnalyticsAPI[analytics.py<br/>Analytics Routes]
        PricingAPI[pricing.py<br/>Pricing Routes]
    end
    
    subgraph "Service Layer - /services/"
        AuthService[auth.py<br/>JWT & Authentication]
        UserService[user_service.py<br/>User Management]
        WalletService[wallet_service.py<br/>Wallet Operations]
        CallService[call_service.py<br/>Call Management]
        AgentService[agent_service.py<br/>Agent CRUD]
        PaymentService[payment_service.py<br/>Payment Processing]
        AnalyticsService[analytics_service.py<br/>Analytics & Reports]
        PricingService[pricing_service.py<br/>Pricing Logic]
    end
    
    subgraph "Database Layer - /database/"
        DBConnection[connection.py<br/>SQLAlchemy Engine]
        DBModels[models.py<br/>ORM Models]
    end
    
    subgraph "Core Engine - /sunona/"
        Assistant[assistant.py<br/>Voice AI Core]
        Models[models.py<br/>Data Models]
        Providers[providers.py<br/>LLM/TTS/STT]
        AssistantMgr[AssistantManager<br/>Orchestration]
    end
    
    subgraph "External Clients"
        WebSocket[WebSocket Client<br/>Real-time Voice]
        HTTPClient[HTTP Client<br/>REST API]
    end
    
    %% Entry Point Connections
    Server -->|includes| APIRouter
    Server -->|startup event| DBConnection
    Server -->|WebSocket /chat/v1| AssistantMgr
    
    %% API Router Connections
    APIRouter -->|includes| AuthAPI
    APIRouter -->|includes| WalletAPI
    APIRouter -->|includes| CallsAPI
    APIRouter -->|includes| AgentsAPI
    APIRouter -->|includes| PaymentsAPI
    APIRouter -->|includes| AnalyticsAPI
    APIRouter -->|includes| PricingAPI
    
    %% API to Service Connections
    AuthAPI -->|uses| AuthService
    AuthAPI -->|uses| UserService
    WalletAPI -->|uses| WalletService
    WalletAPI -->|uses| AuthService
    CallsAPI -->|uses| CallService
    CallsAPI -->|uses| AuthService
    AgentsAPI -->|uses| AgentService
    AgentsAPI -->|uses| AuthService
    PaymentsAPI -->|uses| PaymentService
    PaymentsAPI -->|uses| AuthService
    AnalyticsAPI -->|uses| AnalyticsService
    AnalyticsAPI -->|uses| AuthService
    PricingAPI -->|uses| PricingService
    PricingAPI -->|uses| AuthService
    
    %% Service to Database Connections
    UserService -->|queries| DBModels
    WalletService -->|queries| DBModels
    CallService -->|queries| DBModels
    AgentService -->|queries| DBModels
    PaymentService -->|queries| DBModels
    AnalyticsService -->|queries| DBModels
    PricingService -->|queries| DBModels
    
    %% Database Internal
    DBModels -->|uses| DBConnection
    
    %% Voice AI Engine
    AssistantMgr -->|uses| Assistant
    AssistantMgr -->|uses| Models
    Assistant -->|uses| Providers
    
    %% Client Connections
    HTTPClient -->|HTTP/REST| Server
    WebSocket -->|WebSocket| Server
    
    style Server fill:#4CAF50,stroke:#2E7D32,color:#fff
    style APIRouter fill:#2196F3,stroke:#1565C0,color:#fff
    style DBConnection fill:#FF9800,stroke:#E65100,color:#fff
    style AssistantMgr fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## Request Flow Examples

### 1️⃣ **Authentication Flow**

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant AuthAPI
    participant AuthService
    participant UserService
    participant Database
    
    Client->>Server: POST /api/v1/auth/register
    Server->>AuthAPI: Route to auth.py
    AuthAPI->>UserService: create_user()
    UserService->>Database: INSERT user
    Database-->>UserService: user_id
    UserService-->>AuthAPI: user object
    AuthAPI->>AuthService: create_access_token()
    AuthService-->>AuthAPI: JWT token
    AuthAPI-->>Client: {token, user}
```

### 2️⃣ **Wallet Transaction Flow**

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant WalletAPI
    participant AuthService
    participant WalletService
    participant Database
    
    Client->>Server: POST /api/v1/wallet/add-credits
    Server->>WalletAPI: Route to wallet.py
    WalletAPI->>AuthService: get_current_user_id()
    AuthService-->>WalletAPI: user_id
    WalletAPI->>WalletService: add_credits(user_id, amount)
    WalletService->>Database: UPDATE wallet + INSERT transaction
    Database-->>WalletService: success
    WalletService-->>WalletAPI: new_balance
    WalletAPI-->>Client: {balance, transaction}
```

### 3️⃣ **Voice Call Flow (WebSocket)**

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant AssistantMgr
    participant Assistant
    participant Providers
    participant Database
    
    Client->>Server: WebSocket /chat/v1/{agent_id}
    Server->>AssistantMgr: Create manager
    AssistantMgr->>Assistant: Initialize
    Assistant->>Providers: Load LLM/TTS/STT
    
    loop Voice Conversation
        Client->>AssistantMgr: Audio chunk
        AssistantMgr->>Providers: STT transcribe
        Providers-->>AssistantMgr: text
        AssistantMgr->>Providers: LLM generate
        Providers-->>AssistantMgr: response
        AssistantMgr->>Providers: TTS synthesize
        Providers-->>AssistantMgr: audio
        AssistantMgr-->>Client: Audio response
    end
    
    AssistantMgr->>Database: Save call record & costs
```

---

## Component Interconnections

### 📁 **Directory Structure & Dependencies**

````carousel
### Entry Point
**File:** `local_setup/local_server.py`

**Imports:**
```python
from database.connection import init_db
from api.v1 import api_router
from sunona.agent_manager.assistant_manager import AssistantManager
```

**Responsibilities:**
- FastAPI app initialization
- CORS middleware
- Database startup
- API router inclusion
- WebSocket endpoint
- Legacy MockRedis endpoints

<!-- slide -->

### API Layer
**Directory:** `api/v1/`

**Files & Routes:**
- `auth.py` → `/api/v1/auth/*`
- `wallet.py` → `/api/v1/wallet/*`
- `calls.py` → `/api/v1/calls/*`
- `agents.py` → `/api/v1/agents/*`
- `payments.py` → `/api/v1/payments/*`
- `analytics.py` → `/api/v1/analytics/*`
- `pricing.py` → `/api/v1/pricing/*`

**Common Pattern:**
```python
from services.auth import get_current_user_id
from services.{module}_service import {module}_service
```

<!-- slide -->

### Service Layer
**Directory:** `services/`

**Files:**
- `auth.py` - JWT token creation/validation
- `user_service.py` - User CRUD operations
- `wallet_service.py` - Wallet & transactions
- `call_service.py` - Call records & tracking
- `agent_service.py` - Agent management
- `payment_service.py` - Payment processing
- `analytics_service.py` - Analytics & reports
- `pricing_service.py` - Cost calculations

**Common Pattern:**
```python
from database.models import User, Wallet, Call, etc.
from database.connection import SessionLocal
```

<!-- slide -->

### Database Layer
**Directory:** `database/`

**Files:**
- `connection.py` - SQLAlchemy engine & session
- `models.py` - ORM models (User, Wallet, Call, Agent, etc.)

**Models:**
```python
User, Wallet, WalletTransaction, Call, 
Agent, Payment, PricingConfig
```

**Connection:**
```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
```

<!-- slide -->

### Voice AI Engine
**Directory:** `sunona/`

**Key Files:**
- `assistant.py` - Core voice AI logic
- `models.py` - Pydantic models
- `providers.py` - LLM/TTS/STT providers
- `agent_manager/assistant_manager.py` - Orchestration

**Integration:**
- Used by WebSocket endpoint
- Handles real-time voice conversations
- Tracks usage for billing
````

---

## Data Flow Summary

### 🔄 **Complete Request Lifecycle**

```mermaid
graph LR
    A[Client Request] --> B{Request Type}
    B -->|HTTP REST| C[API Router]
    B -->|WebSocket| D[AssistantManager]
    
    C --> E[API Endpoint]
    E --> F[Auth Middleware]
    F --> G[Service Layer]
    G --> H[Database]
    H --> I[Response]
    I --> A
    
    D --> J[Voice AI Engine]
    J --> K[Providers]
    K --> L[Real-time Audio]
    L --> A
    
    J --> H
```

### 🔐 **Authentication Flow**

1. **Client** sends credentials
2. **AuthAPI** receives request
3. **UserService** validates against **Database**
4. **AuthService** generates JWT token
5. Token returned to **Client**
6. Subsequent requests include token in header
7. **AuthService** validates token via `get_current_user_id()`

### 💰 **Wallet & Billing Flow**

1. **Client** requests wallet operation
2. **WalletAPI** authenticates user
3. **WalletService** performs transaction
4. **Database** updates wallet & creates transaction record
5. **PricingService** calculates costs
6. Balance returned to **Client**

### 📞 **Voice Call Flow**

1. **Client** connects via WebSocket
2. **Server** creates **AssistantManager**
3. **AssistantManager** loads agent config
4. **Voice AI Engine** processes audio
5. **Providers** handle STT/LLM/TTS
6. **CallService** tracks usage & costs
7. Real-time audio streamed to **Client**

---

## Key Integration Points

| Component | Depends On | Used By |
|-----------|------------|---------|
| **local_server.py** | api.v1, database, sunona | All clients |
| **api/v1/** | services | local_server.py |
| **services/** | database.models | api/v1/ |
| **database/** | - | services/, sunona/ |
| **sunona/** | database (optional) | local_server.py |

---

## Technology Stack

- **Framework:** FastAPI
- **Database:** SQLAlchemy ORM
- **Authentication:** JWT (python-jose)
- **Real-time:** WebSocket
- **Voice AI:** Sunona Engine (LLM/TTS/STT)
- **Server:** Uvicorn ASGI
