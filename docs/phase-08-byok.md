# Phase 8: BYOK (Bring Your Own Key)

## Overview

AgentForge is a **Pure BYOK** platform. Users must register their own LLM API keys to use the pipeline.
Keys are encrypted at rest with AES-256-GCM and never exposed in full.

Supported providers: **OpenAI**, **Anthropic**, **Google Gemini**

## Architecture

```
User registers key -> AES-256-GCM encryption -> DB storage (user_llm_keys)
Pipeline execution -> Decrypt key -> Create per-user LLMRouter -> Agent nodes use user's key
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Encryption | `backend/shared/encryption.py` | AES-256-GCM encrypt/decrypt |
| DB Model | `backend/shared/models.py` | `UserLLMKey` with unique (user, provider) |
| Migration | `backend/alembic/versions/0005_user_llm_keys.py` | DB schema |
| LLM Router | `backend/pipeline/llm_router.py` | Multi-provider routing with BYOK keys |
| Router Factory | `backend/pipeline/user_router_factory.py` | Per-user router with TTL cache |
| Key Validator | `backend/pipeline/key_validator.py` | Provider-specific key validation |
| API Routes | `backend/gateway/routes/llm_keys.py` | CRUD + validation endpoints |
| Settings UI | `frontend/app/(main)/settings/page.tsx` | Key management page |

## Setup Guide

### 1. Generate Encryption Key

```bash
python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

### 2. Configure Environment

Add to `.env` (or export in shell):

```bash
ENCRYPTION_KEY=<generated-key-from-step-1>
```

### 3. Start Services

```bash
cd docker
docker compose up -d
```

### 4. Register API Keys

1. Sign up / Log in
2. Navigate to **Settings** (sidebar)
3. Click **Add Key** on a provider card (OpenAI / Anthropic / Google)
4. Enter your API key
5. Key is validated and encrypted automatically
6. Status badge shows **Valid** or **Invalid**

### 5. Run a Pipeline

With at least one valid key registered, pipelines will use your keys automatically.
The LLM Router selects the best available provider based on your registered keys.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/llm-keys` | Register or update a key (upsert per provider) |
| `GET` | `/api/v1/llm-keys` | List keys (masked, key_prefix only) |
| `DELETE` | `/api/v1/llm-keys/{key_id}` | Delete a key |
| `POST` | `/api/v1/llm-keys/{key_id}/validate` | Re-validate a key |

## Security

- **Encryption**: AES-256-GCM with per-key random nonce
- **Storage**: Only ciphertext + nonce stored in DB, never plaintext
- **Display**: Only first 12 characters shown as `key_prefix`
- **Logs**: Keys never written to logs (only prefix)
- **API responses**: Full key never returned
- **Decryption**: Only at pipeline execution time (minimizes memory exposure)
- **Cache**: TTL 5 minutes, max 200 entries (limits in-memory key lifetime)
- **IDOR prevention**: All queries filter by `user_id`, non-owner gets 404

## Provider-Specific Notes

### OpenAI
- Key format: `sk-...` or `sk-proj-...`
- Validation: calls `client.models.list()`
- Models: GPT-4o, GPT-4o-mini, GPT-3.5-turbo

### Anthropic
- Key format: `sk-ant-...`
- Validation: sends minimal message to Claude Haiku (max_tokens=1)
- Models: Claude 3.5 Sonnet, Claude 3 Haiku

### Google Gemini
- Key format: `AIza...`
- Validation: calls `client.models.list()`
- Models: Gemini 2.0 Flash, Gemini 2.5 Pro

## Implementation Phases

| Phase | PR | Description |
|-------|-----|-------------|
| 8-1 | #62 | DB model + AES-256-GCM encryption |
| 8-2 | #64 | LLM Router refactoring + Gemini support |
| 8-3 | #66 | User Router Factory + Key Validator |
| 8-4 | #68 | API endpoints + Pipeline integration |
| 8-5 | #70 | Frontend Settings page |
| 8-6 | #72 | Docker + Documentation |
