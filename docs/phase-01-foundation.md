# Phase 1: Project Foundation and Basic Chatbot UI

## Overview

Phase 1 establishes the foundational infrastructure for AgentForge, a Korean-native multi-agent platform. This phase delivers a working chatbot interface with real-time WebSocket communication, persistent conversation storage, and a containerized development environment.

**Goals:**
- Set up monorepo structure for frontend, backend, and data collector services
- Implement basic chatbot UI with real-time messaging
- Create REST API for conversation and message management
- Establish database persistence with PostgreSQL
- Configure Docker Compose for local development
- Set up CI/CD pipelines with automated testing and linting

**Deliverables:**
- Functional chat interface accessible at http://localhost:3000
- RESTful API with WebSocket support at http://localhost:8000
- Containerized development environment with hot-reload
- Automated tests and code quality checks
- Complete project documentation

## Architecture

Phase 1 implements a simplified version of the full AgentForge architecture, focusing on core communication infrastructure:

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14+ (App Router) | Modern React framework with server components |
| **UI Framework** | Tailwind CSS | Utility-first CSS for rapid development |
| **Backend** | FastAPI | High-performance async Python web framework |
| **Database** | PostgreSQL 16 | Relational database for structured data |
| **Cache** | Redis 7 | In-memory cache for sessions and real-time data |
| **ORM** | SQLAlchemy 2.0+ (Async) | Type-safe database operations |
| **WebSocket** | FastAPI WebSocket | Real-time bidirectional communication |
| **Container** | Docker Compose | Local development environment orchestration |
| **CI/CD** | GitHub Actions | Automated testing, linting, and code review |

### System Components

```
┌─────────────────┐
│   Browser       │
│  (Next.js UI)   │
└────────┬────────┘
         │ HTTP/WS
         │
┌────────▼────────┐
│   API Gateway   │
│   (FastAPI)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ PostgreSQL │ │  Redis  │
│ (Persistence) │ │ (Cache) │
└───────────┘ └─────────┘
```

**Data Flow:**
1. User sends message via WebSocket from Next.js frontend
2. FastAPI backend receives message and stores in PostgreSQL
3. Backend processes message (Phase 1: echo; later phases: LLM processing)
4. Response sent back through WebSocket connection
5. Frontend updates UI with new message in real-time

## Directory Structure

```
AgentForge/
├── .github/
│   └── workflows/               # CI/CD pipelines
│       ├── test.yml            # Automated testing
│       ├── lint.yml            # Code quality checks
│       └── claude-code-review.yml  # AI-powered code review
│
├── frontend/                    # Next.js frontend application
│   ├── src/
│   │   ├── app/                # Next.js App Router
│   │   │   ├── page.tsx       # Home page with chat interface
│   │   │   ├── layout.tsx     # Root layout
│   │   │   └── globals.css    # Global styles
│   │   ├── components/         # React components
│   │   │   ├── ChatWindow.tsx # Main chat interface
│   │   │   ├── MessageBubble.tsx  # Individual message display
│   │   │   └── MessageInput.tsx   # Message input field
│   │   └── lib/                # Utilities and hooks
│   │       └── websocket.ts   # WebSocket client with reconnection
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
│
├── backend/                     # FastAPI backend services
│   ├── shared/                  # Shared models and utilities
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schemas.py          # Pydantic validation schemas
│   │   ├── database.py         # Database connection and session
│   │   └── config.py           # Configuration management
│   ├── api_gateway/             # API Gateway service (Phase 1 focus)
│   │   ├── main.py             # FastAPI application entry
│   │   ├── routes/             # API route handlers
│   │   │   ├── health.py      # Health check endpoint
│   │   │   ├── conversations.py  # Conversation CRUD
│   │   │   └── websocket.py   # WebSocket chat handler
│   │   └── dependencies.py     # Dependency injection
│   ├── discussion_engine/       # (Phase 2+)
│   ├── pipeline_orchestrator/   # (Phase 3+)
│   └── requirements.txt
│
├── data-collector/              # (Phase 4+)
│   └── requirements.txt
│
├── docker/                      # Docker configuration
│   ├── docker-compose.yml      # Service orchestration
│   ├── Dockerfile.frontend     # Frontend container
│   ├── Dockerfile.backend      # Backend container
│   ├── Dockerfile.collector    # Data collector container (Phase 4+)
│   └── .env.example            # Environment variables template
│
├── tests/                       # Test suites
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
│
├── docs/                        # Documentation
│   ├── phase-01-foundation.md  # This document
│   ├── architecture.md         # System architecture (TBD)
│   └── api-reference.md        # API documentation (TBD)
│
└── README.md                    # Project overview
```

## Database Schema

Phase 1 implements three core tables for user management and conversation persistence:

### Users Table

Stores user accounts with role-based access control foundation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique user identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| `hashed_password` | VARCHAR(255) | NOT NULL | bcrypt hashed password |
| `display_name` | VARCHAR(100) | NOT NULL | User display name (supports Korean) |
| `role` | ENUM | NOT NULL, DEFAULT 'free' | User role (free, pro, admin) |
| `created_at` | TIMESTAMP | NOT NULL | Account creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last update timestamp |

**Indexes:**
- Primary: `id`
- Unique: `email`

**Notes:**
- Phase 1: Password hashing implemented, authentication in Phase 2
- Korean character support via UTF-8 encoding in `display_name`

### Conversations Table

Stores conversation sessions between users and the AI system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique conversation identifier |
| `user_id` | UUID | FOREIGN KEY (users.id), NOT NULL | Owner of the conversation |
| `title` | VARCHAR(255) | NOT NULL | Conversation title (auto-generated or user-set) |
| `status` | ENUM | NOT NULL, DEFAULT 'active' | Conversation status (active, archived) |
| `created_at` | TIMESTAMP | NOT NULL | Conversation start timestamp |
| `updated_at` | TIMESTAMP | NOT NULL | Last message timestamp |

**Indexes:**
- Primary: `id`
- Foreign Key: `user_id` (CASCADE DELETE)
- Index: `user_id, status` (for fast user conversation queries)

**Notes:**
- Titles support Korean characters
- Archiving preserves conversation history without deletion

### Messages Table

Stores individual messages within conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Unique message identifier |
| `conversation_id` | UUID | FOREIGN KEY (conversations.id), NOT NULL | Parent conversation |
| `role` | ENUM | NOT NULL | Message role (user, assistant, system) |
| `content` | TEXT | NOT NULL | Message content (supports Korean) |
| `metadata_` | JSONB | NULLABLE | Additional metadata (timestamps, model info, etc.) |
| `created_at` | TIMESTAMP | NOT NULL | Message creation timestamp |

**Indexes:**
- Primary: `id`
- Foreign Key: `conversation_id` (CASCADE DELETE)
- Index: `conversation_id, created_at` (for chronological message retrieval)

**Notes:**
- JSONB metadata for extensibility (token counts, model versions, etc.)
- Full Korean language support in `content` field

### Entity Relationships

```
users (1) ──< (N) conversations ──< (N) messages
```

- One user can have many conversations
- One conversation can have many messages
- Cascade delete: Deleting a user removes all their conversations and messages
- Cascade delete: Deleting a conversation removes all its messages

## API Endpoints

Phase 1 implements a RESTful API with WebSocket support for real-time chat:

### Health Check

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/api/v1/health` | System health and version check | No |

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Conversation Management

#### Create Conversation

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `POST` | `/api/v1/conversations` | Create a new conversation | No (Phase 2: Yes) |

**Request Body:**
```json
{
  "title": "New Chat Session",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"  // Optional in Phase 1
}
```

**Response (201 Created):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "New Chat Session",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### List Conversations

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/api/v1/conversations?user_id={uuid}` | List all conversations for a user | No (Phase 2: Yes) |

**Query Parameters:**
- `user_id` (UUID): Filter by user ID
- `status` (optional): Filter by status (active, archived)
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "conversations": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Chat about agents",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### Get Conversation Details

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/api/v1/conversations/{conversation_id}` | Get conversation with message history | No (Phase 2: Yes) |

**Response (200 OK):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Chat about agents",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "messages": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "role": "user",
      "content": "Hello, how are you?",
      "created_at": "2024-01-15T10:30:15Z"
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655440003",
      "role": "assistant",
      "content": "Hello! I'm doing well. How can I help you today?",
      "created_at": "2024-01-15T10:30:18Z"
    }
  ]
}
```

### WebSocket Chat

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `WS` | `/api/v1/ws/chat/{conversation_id}` | Real-time chat WebSocket connection | No (Phase 2: Yes) |

**Connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/chat/${conversationId}`);
```

**Client → Server Message:**
```json
{
  "type": "user_message",
  "content": "What can you do?",
  "timestamp": "2024-01-15T10:30:20Z"
}
```

**Server → Client Message:**
```json
{
  "type": "assistant_message",
  "content": "I can help you with various tasks...",
  "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-01-15T10:30:22Z"
}
```

**Status Messages:**
```json
{
  "type": "status",
  "content": "Connected to conversation",
  "timestamp": "2024-01-15T10:30:19Z"
}
```

**Error Handling:**
- WebSocket disconnects: Client auto-reconnects with exponential backoff
- Invalid messages: Server sends error type message
- Connection limits: Max 100 concurrent connections per conversation

## Frontend Components

### ChatWindow Component

Main chat interface component that manages WebSocket connection and message display.

**Location:** `frontend/src/components/ChatWindow.tsx`

**Features:**
- WebSocket connection management with auto-reconnect
- Real-time message streaming
- Scroll-to-bottom on new messages
- Loading states and error handling
- Korean text support with proper font rendering

**Props:**
```typescript
interface ChatWindowProps {
  conversationId: string;
  onError?: (error: Error) => void;
}
```

**State Management:**
- Messages array (user and assistant messages)
- Connection status (connecting, connected, disconnected, error)
- Loading state for message sending
- Auto-scroll reference for message container

### MessageBubble Component

Individual message display component with role-based styling.

**Location:** `frontend/src/components/MessageBubble.tsx`

**Features:**
- Role-based styling (user: blue, assistant: gray)
- Timestamp display
- Markdown rendering support (Phase 2+)
- Korean text wrapping and line breaks

**Props:**
```typescript
interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}
```

### MessageInput Component

Message input field with send button and keyboard shortcuts.

**Location:** `frontend/src/components/MessageInput.tsx`

**Features:**
- Auto-expanding textarea
- Enter to send (Shift+Enter for new line)
- Character limit indicator (optional)
- Korean IME (Input Method Editor) support
- Disabled state during message sending

**Props:**
```typescript
interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}
```

### WebSocket Client Utility

Reusable WebSocket client with reconnection logic.

**Location:** `frontend/src/lib/websocket.ts`

**Features:**
- Automatic reconnection with exponential backoff
- Connection state management
- Type-safe message handling
- Error recovery and retry logic
- Heartbeat/ping-pong for connection health

**Usage:**
```typescript
const client = new WebSocketClient(`ws://localhost:8000/api/v1/ws/chat/${id}`);

client.onMessage((message) => {
  console.log('Received:', message);
});

client.onError((error) => {
  console.error('WebSocket error:', error);
});

client.connect();
```

## Docker Services

Phase 1 uses Docker Compose to orchestrate all services for local development:

### Service Configuration

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `frontend` | Custom (Node 20) | 3000 | Next.js development server |
| `backend` | Custom (Python 3.11) | 8000 | FastAPI application |
| `postgres` | postgres:16-alpine | 5432 | PostgreSQL database |
| `redis` | redis:7-alpine | 6379 | Redis cache |
| `pgadmin` | dpage/pgadmin4 | 5050 | Database management UI (optional) |

### Docker Compose Configuration

**Location:** `docker/docker-compose.yml`

**Key Features:**
- Hot-reload for both frontend and backend
- Volume mounts for source code
- Health checks for all services
- Dependency ordering (backend waits for postgres + redis)
- Environment variable configuration via `.env` file

**Service Details:**

#### Frontend Service
- Base: `node:20-alpine`
- Working Dir: `/app`
- Command: `npm run dev`
- Volumes: `./frontend:/app`, `node_modules` cache
- Environment: `NEXT_PUBLIC_API_URL=http://localhost:8000`

#### Backend Service
- Base: `python:3.11-slim`
- Working Dir: `/app`
- Command: `uvicorn api_gateway.main:app --host 0.0.0.0 --reload`
- Volumes: `./backend:/app`
- Environment: Database URL, Redis URL, API keys
- Depends On: `postgres`, `redis`

#### PostgreSQL Service
- Base: `postgres:16-alpine`
- Volumes: `pgdata:/var/lib/postgresql/data`
- Environment: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Health Check: `pg_isready`

#### Redis Service
- Base: `redis:7-alpine`
- Volumes: `redisdata:/data`
- Health Check: `redis-cli ping`

### Environment Variables

**Location:** `docker/.env.example`

Required variables:
```bash
# Database
POSTGRES_DB=agentforge
POSTGRES_USER=agentforge
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://redis:6379

# Backend
DATABASE_URL=postgresql+asyncpg://agentforge:your_secure_password@postgres:5432/agentforge
SECRET_KEY=your_secret_key_here

# API Keys (Phase 2+)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
NAVER_API_KEY=...
```

## Running Locally

### Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- Git

### Step-by-Step Setup

1. **Clone the repository:**
```bash
git clone https://github.com/Maroco0109/AgentForge.git
cd AgentForge
```

2. **Configure environment variables:**
```bash
cd docker
cp .env.example .env
# Edit .env and set your passwords and API keys
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Verify services are running:**
```bash
docker-compose ps
```

Expected output:
```
NAME                STATUS    PORTS
agentforge-frontend-1   running   0.0.0.0:3000->3000/tcp
agentforge-backend-1    running   0.0.0.0:8000->8000/tcp
agentforge-postgres-1   running   0.0.0.0:5432->5432/tcp
agentforge-redis-1      running   0.0.0.0:6379->6379/tcp
```

5. **Initialize database:**
```bash
docker-compose exec backend python -m alembic upgrade head
```

6. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### Development Workflow

**Hot Reload:**
- Frontend: Changes to `frontend/src/**` trigger automatic rebuild
- Backend: Changes to `backend/**/*.py` trigger uvicorn reload

**View Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Database Access:**
```bash
# psql client
docker-compose exec postgres psql -U agentforge -d agentforge

# pgAdmin (if enabled)
# Open http://localhost:5050
# Login with credentials from .env
```

**Stop Services:**
```bash
# Stop without removing containers
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v
```

## Testing

Phase 1 includes foundational test infrastructure:

### Test Organization

```
tests/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_models.py        # Database model tests
│   ├── test_schemas.py       # Pydantic schema validation tests
│   └── test_websocket.py     # WebSocket handler unit tests
│
├── integration/               # Integration tests (database, API)
│   ├── test_api_conversations.py  # Conversation CRUD tests
│   ├── test_websocket_chat.py     # WebSocket integration tests
│   └── test_database.py      # Database operation tests
│
└── e2e/                       # End-to-end tests (Phase 2+)
    └── test_chat_flow.py     # Full chat flow tests
```

### Running Tests

**Backend Tests:**
```bash
# Run all backend tests
docker-compose exec backend pytest tests/ -v

# Run with coverage
docker-compose exec backend pytest tests/ --cov=backend --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/unit/test_models.py -v
```

**Frontend Tests (Phase 2+):**
```bash
# Run Jest tests
docker-compose exec frontend npm test

# Run with coverage
docker-compose exec frontend npm test -- --coverage
```

### Test Database

Tests use a separate test database to avoid polluting development data:

**Configuration:**
- Database: `agentforge_test`
- Automatic teardown after test suite
- Fixtures for common test data

**Example Test:**
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User, Conversation
from backend.shared.database import get_db

@pytest.mark.asyncio
async def test_create_conversation(db_session: AsyncSession):
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        display_name="Test User"
    )
    db_session.add(user)
    await db_session.commit()

    # Create conversation
    conversation = Conversation(
        user_id=user.id,
        title="Test Conversation"
    )
    db_session.add(conversation)
    await db_session.commit()

    # Verify
    assert conversation.id is not None
    assert conversation.status == ConversationStatus.ACTIVE
```

## CI/CD Pipeline

### GitHub Actions Workflows

**Location:** `.github/workflows/`

#### 1. Test Workflow (`test.yml`)

**Triggers:**
- All pull requests
- Pushes to `main` and `develop` branches

**Jobs:**
- `backend-test`: Runs pytest with PostgreSQL and Redis services
- `frontend-build`: Verifies Next.js build succeeds

**Environment:**
- PostgreSQL 16 (test database)
- Redis 7
- Python 3.11
- Node.js 20

#### 2. Lint Workflow (`lint.yml`)

**Triggers:**
- All pull requests
- Pushes to `main` and `develop` branches

**Jobs:**
- `backend-lint`: Runs Ruff (fast Python linter/formatter)
- `frontend-lint`: Runs ESLint with Next.js config

**Quality Gates:**
- Zero linting errors required to pass
- Code formatting automatically checked

#### 3. Claude Code Review (`claude-code-review.yml`)

**Triggers:**
- Pull requests opened or updated
- Targeting `main` or `develop` branches

**Focus Areas:**
- Security vulnerabilities (OWASP Top 10)
- Prompt injection risks (LLM-specific)
- Code quality and error handling
- Test coverage gaps
- Performance concerns (N+1 queries, etc.)

**AI Review Scope:**
- Critical: Security, bugs, data leaks
- Important: Code quality, test coverage
- Agent-specific: LLM safety, cost efficiency

### Required Secrets

Configure in GitHub repository settings:

| Secret | Purpose | Required For |
|--------|---------|--------------|
| `ANTHROPIC_API_KEY` | Claude Code Review | CI/CD |
| `OPENAI_API_KEY` | LLM features (Phase 2+) | Deployment |
| `DATABASE_URL` | Production database | Deployment |

## Korean Language Support

Phase 1 includes full Korean language support:

### Database Configuration
- UTF-8 encoding for all text fields
- Proper collation for Korean sorting
- Text fields support Hangul characters

### Frontend Configuration
- Korean web fonts (Noto Sans KR, Pretendard)
- Proper line-breaking for Korean text
- IME (Input Method Editor) support in text inputs
- Right-to-left text handling for mixed content

### Example Korean Text Handling
```typescript
// Korean character detection
const hasKorean = /[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(text);

// Apply Korean-specific line breaking
<p className="break-words whitespace-pre-wrap lang-ko">
  {koreanText}
</p>
```

## Performance Considerations

Phase 1 establishes performance baseline:

### Database
- Indexed foreign keys for fast joins
- Connection pooling (SQLAlchemy async engine)
- Query optimization for conversation listing

### WebSocket
- Connection limit: 100 concurrent per conversation
- Message rate limiting: 10 messages/second per user
- Auto-reconnect with exponential backoff

### Frontend
- React Server Components for initial render
- Client-side state for real-time updates
- Lazy loading for conversation history

### Monitoring (Phase 2+)
- Response time tracking
- Error rate monitoring
- WebSocket connection metrics

## Security Baseline

Phase 1 establishes security foundation:

### Current Implementation
- Environment variable configuration (no hardcoded secrets)
- CORS configuration for API endpoints
- Input validation via Pydantic schemas
- SQL injection protection (SQLAlchemy ORM)

### Phase 2 Additions
- JWT authentication
- Password hashing with bcrypt
- Rate limiting per user
- CSRF protection
- Content Security Policy headers

## Known Limitations

Phase 1 is intentionally limited in scope:

1. **No Authentication:** User IDs manually specified (added in Phase 2)
2. **No LLM Integration:** Echo responses only (added in Phase 2)
3. **No File Upload:** Text-only messages (added in Phase 3)
4. **No Multi-Agent Pipeline:** Single conversation thread (added in Phase 3)
5. **No Production Deployment:** Docker Compose only (Kubernetes in Phase 5)

## Success Criteria

Phase 1 is complete when:

- [ ] All Docker services start successfully
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend health check returns 200 OK
- [ ] Create conversation API endpoint works
- [ ] List conversations API endpoint works
- [ ] WebSocket connection established
- [ ] Messages sent and received in real-time
- [ ] Messages persisted to PostgreSQL
- [ ] All backend tests pass
- [ ] Frontend builds without errors
- [ ] CI/CD pipelines pass on GitHub
- [ ] Documentation complete and accurate

## Next Steps

### Phase 2: Authentication and Authorization
- Implement NextAuth.js v5 for frontend
- Add JWT authentication to backend
- User registration and login flows
- Role-based access control (RBAC)
- Secure conversation access (users can only see their own)

### Phase 3: LLM Integration
- OpenAI API integration
- Anthropic Claude API integration
- Multi-LLM routing logic
- Streaming responses via WebSocket
- Token usage tracking

### Phase 4: Discussion Engine
- Intent analysis from user prompts
- Multi-round design conversation (3-5 rounds)
- Design critique and iteration
- Plan approval workflow

### Phase 5: Pipeline Orchestrator
- LangGraph integration
- Dynamic agent pipeline construction
- Multi-agent coordination
- State management across agents

## Troubleshooting

### Common Issues

**Issue: Docker containers fail to start**
```bash
# Check logs
docker-compose logs

# Rebuild images
docker-compose build --no-cache
docker-compose up -d
```

**Issue: Frontend can't connect to backend**
- Verify `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Check CORS configuration in backend
- Ensure backend is running: `docker-compose ps`

**Issue: Database connection errors**
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check credentials in `docker/.env`
- Verify `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host:port/db`

**Issue: WebSocket connection fails**
- Check conversation ID is valid UUID
- Verify backend WebSocket endpoint: `ws://localhost:8000/api/v1/ws/chat/{id}`
- Check browser console for errors

**Issue: Tests fail**
```bash
# Reset test database
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head

# Run tests with verbose output
docker-compose exec backend pytest tests/ -vv
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## Changelog

### v0.1.0 (Phase 1 - 2024-01-15)
- Initial project setup
- Basic chatbot UI with WebSocket
- REST API for conversations
- PostgreSQL database schema
- Docker Compose development environment
- CI/CD pipelines with GitHub Actions
- Korean language support
