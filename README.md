# AgentForge

## Overview

AgentForge is a user-prompt driven multi-agent platform that acts as a "business partner" for AI-powered solution development. Users describe their requirements in natural language, and the AI system engages in deep conversational design discussions (3-5 rounds) before automatically designing and executing agent-based pipelines to fulfill the request.

This platform transforms vague ideas into production-ready solutions through intelligent discussion, progressive implementation, and automated orchestration.

## Key Differentiators

- **Deep Discussion-Based Design**: AI acts as a business partner, engaging in multi-round conversations to understand requirements, propose designs, and iterate based on feedback
- **Phase-by-Phase Progressive Implementation**: Systematic development with documentation generated at each phase
- **Data Collection Legality Auto-Verification**: Built-in compliance checking for web scraping and data collection activities
- **Native Korean Language Support**: First-class support for Korean language processing and interfaces
- **Multi-LLM Routing**: Intelligent routing across OpenAI, Anthropic, and Naver models for cost optimization and capability matching

## Architecture

AgentForge is built as a microservices architecture with five core services:

### 1. Frontend Service (Next.js)
Provides a modern chatbot interface and visual pipeline builder for users to interact with the platform. Supports real-time conversation and pipeline visualization.

### 2. API Gateway (FastAPI)
Central entry point handling authentication, role-based access control (RBAC), rate limiting, and request routing to downstream services.

### 3. Discussion Engine
Performs intent analysis, design generation, and design critique through multi-round conversational workflows. Orchestrates the business partner experience.

### 4. Pipeline Orchestrator (LangGraph)
Dynamically constructs and executes agent-based pipelines based on approved designs. Manages agent coordination, state, and execution flow.

### 5. Data Collector (Microservice)
Specialized service for web crawling, PDF parsing, and compliance verification. Ensures all data collection activities meet legal requirements.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14+, React 18+ |
| Auth | NextAuth.js v5 |
| Backend | FastAPI, Python 3.11+ |
| Agent Framework | LangGraph |
| LLM | OpenAI + Anthropic + Naver (Multi-LLM Routing) |
| Database | PostgreSQL 16+ |
| Cache | Redis 7+ |
| Vector DB | Chroma |
| File Storage | MinIO |
| Container | Docker Compose (development) → Kubernetes (production) |

## Getting Started

### Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/Maroco0109/AgentForge.git
cd AgentForge

# Start all services
docker-compose up -d

# Access the application
open http://localhost:3000
```

The default setup includes:
- Frontend: `http://localhost:3000`
- API Gateway: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO Console: `http://localhost:9001`

### Environment Configuration

Copy the example environment files and configure:

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

Update the following required variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `NAVER_API_KEY`: Your Naver Cloud API key (optional)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`: MinIO credentials

## Project Structure

```
AgentForge/
├── frontend/               # Next.js frontend application
│   ├── src/
│   │   ├── app/           # Next.js app router pages
│   │   ├── components/    # React components
│   │   └── lib/           # Utilities and hooks
│   └── package.json
│
├── backend/               # FastAPI backend services
│   ├── api_gateway/       # API Gateway service
│   ├── discussion_engine/ # Discussion Engine service
│   ├── pipeline_orchestrator/ # Pipeline Orchestrator service
│   └── requirements.txt
│
├── data-collector/        # Data collection microservice
│   ├── src/
│   │   ├── crawlers/      # Web crawling modules
│   │   ├── parsers/       # Document parsing modules
│   │   └── compliance/    # Legality verification
│   └── requirements.txt
│
├── docker/                # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── Dockerfile.datacollector
│
├── docs/                  # Documentation
│   ├── architecture.md
│   ├── api-reference.md
│   └── deployment.md
│
├── tests/                 # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── README.md
```

## Development

### Branch Strategy

We follow a Git Flow branching model:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feat/*`: New features
- `fix/*`: Bug fixes
- `refactor/*`: Code refactoring
- `test/*`: Test additions or modifications
- `docs/*`: Documentation updates
- `chore/*`: Maintenance tasks

### Commit Convention

We use conventional commits for clear change history:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance, dependencies, tooling

Example:
```
feat(discussion-engine): add multi-round design critique

Implements iterative design improvement through LLM-based critique.
Supports 3-5 rounds of refinement based on user feedback.

Closes #123
```

### Continuous Integration

GitHub Actions workflows run on every push and pull request:

- **Test**: Unit, integration, and E2E tests
- **Lint**: Code style and quality checks (ESLint, Ruff)
- **Claude Code Review**: AI-powered code review for quality assurance
- **Build**: Docker image builds and security scans

### Local Development

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Backend Services

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload
```

#### Data Collector

```bash
cd data-collector
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## License

MIT License

Copyright (c) 2024 AgentForge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

We welcome contributions from the community. To contribute:

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/AgentForge.git
cd AgentForge
git remote add upstream https://github.com/Maroco0109/AgentForge.git
```

### 2. Create a Feature Branch

```bash
git checkout -b feat/your-feature-name develop
```

### 3. Make Your Changes

- Write clear, tested code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 4. Commit and Push

```bash
git add .
git commit -m "feat(scope): your feature description"
git push origin feat/your-feature-name
```

### 5. Open a Pull Request

- Target the `develop` branch
- Provide a clear description of changes
- Reference any related issues
- Ensure CI checks pass

### Code Review Process

1. Automated CI checks must pass
2. At least one maintainer approval required
3. Claude Code Review feedback should be addressed
4. All discussions resolved before merge

### Reporting Issues

Use GitHub Issues to report bugs or request features. Please include:

- Clear description of the issue or feature
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs or screenshots

### Community Guidelines

- Be respectful and constructive
- Follow the code of conduct
- Help others in discussions
- Share knowledge and improvements

For major changes, please open an issue first to discuss the proposed changes with maintainers.

## Support

- Documentation: [docs/](./docs/)
- Issues: [GitHub Issues](https://github.com/Maroco0109/AgentForge/issues)
- Discussions: [GitHub Discussions](https://github.com/Maroco0109/AgentForge/discussions)

---

Built with care by the AgentForge team.
