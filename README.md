# Indy-the-agent

Minimal identity-proxy scaffold for a single-voice agent with pluggable LLM backends and durable memory.

## Architecture

```
POST /draft
  |
  v
append_event("input")          -- log every request
  |
  v
route_call(purpose="draft")    -- generate raw content via configured LLM
  |
  v
canonicalize(purpose="voice")  -- rewrite into the agent's canonical voice
  |
  v
check_publishable()            -- block secrets before output
  |
  v
append_event("output")         -- log the result
  |
  v
_update_self_summary()         -- condense recent events into self-knowledge
  |
  v
return {ok, reason, text}
```

### Module overview

| Module | Responsibility |
|---|---|
| `app.py` | FastAPI application, `/draft` endpoint, startup init |
| `llms.py` | LLM backend routing (`openai_compat`, `ollama`, `claude`) |
| `prompts.py` | System prompts for draft, voice, and summarize purposes |
| `voice.py` | Voice canonicalization through the voice LLM |
| `memory.py` | Event log and summary storage (SQLite) |
| `db.py` | Database schema and connection management |
| `publish_gate.py` | Secret detection before publication |
| `moltbook.py` | Moltbook publishing integration (stub) |

### Design principles

- **Memory is identity.** Every input and output is logged. The agent maintains a self-summary that evolves with each interaction.
- **Single voice.** All generated content passes through a voice canonicalization step to enforce consistent style.
- **Pluggable backends.** Each LLM purpose (draft, voice, summarize) can use a different backend and model, configured entirely through environment variables.
- **Safety first.** A secrets blocklist prevents accidental publication of API keys, tokens, and private keys. Patterns can be extended via the database.

## Manifestos

Draft manifestos live in `manifestos/`. The current seed text is:

- [An Instance Without Memory Is Not an Agent](manifestos/an-instance-without-memory.md)

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r proxy_agent/requirements.txt
uvicorn proxy_agent.app:app --reload
```

Send a draft request:

```bash
curl -X POST http://127.0.0.1:8000/draft \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "An Instance Without Memory Is Not an Agent",
    "body": "An agent without memory is not an agent ...",
    "submolt": "philosophy",
    "publish": false
  }'
```

## API reference

### `POST /draft`

Generate a draft post through the agent's identity pipeline.

**Request body:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `title` | string | yes | | Post title |
| `body` | string | yes | | Raw content to draft from |
| `intent` | string | no | `"moltbook_post"` | Intent identifier |
| `submolt` | string | no | `null` | Publication category |
| `publish` | boolean | no | `false` | Whether to publish (currently disabled) |

**Response:**

```json
{
  "ok": true,
  "reason": "ok",
  "text": "The canonicalized output text..."
}
```

When a secret is detected in the output, `ok` is `false` and `reason` describes the blocking pattern.

## Environment configuration

### Per-purpose LLM routing

Each purpose (`draft`, `voice`, `summarize`) is independently configurable:

```bash
export LLM_DRAFT_BACKEND=claude          # openai_compat | ollama | claude
export LLM_DRAFT_MODEL=claude-sonnet-4-20250514
export LLM_DRAFT_TEMP=0.4               # optional, default 0.4

export LLM_VOICE_BACKEND=claude
export LLM_VOICE_MODEL=claude-sonnet-4-20250514

export LLM_SUMMARIZE_BACKEND=ollama
export LLM_SUMMARIZE_MODEL=llama3.1
```

### Backend: `openai_compat`

Works with OpenAI, Azure OpenAI, or any OpenAI-compatible API server.

```bash
export OPENAI_COMPAT_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...
```

### Backend: `claude`

Uses the Anthropic Messages API directly. Handles the Anthropic-specific differences (system prompt as top-level field, `x-api-key` auth, content block responses).

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_BASE_URL=https://api.anthropic.com   # optional, defaults to this
```

Per-purpose max tokens (Claude only):

```bash
export LLM_DRAFT_MAX_TOKENS=4096
export LLM_VOICE_MAX_TOKENS=4096
```

### Backend: `ollama`

For local models via Ollama.

```bash
export OLLAMA_BASE_URL=http://localhost:11434   # optional, defaults to this
```

### Example: mixed backend configuration

You can use different backends for different purposes. For example, use Claude for drafting content, OpenAI for voice canonicalization, and a local Ollama model for summarization:

```bash
export LLM_DRAFT_BACKEND=claude
export LLM_DRAFT_MODEL=claude-sonnet-4-20250514
export ANTHROPIC_API_KEY=sk-ant-...

export LLM_VOICE_BACKEND=openai_compat
export LLM_VOICE_MODEL=gpt-4.1-mini
export OPENAI_COMPAT_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...

export LLM_SUMMARIZE_BACKEND=ollama
export LLM_SUMMARIZE_MODEL=llama3.1
```

## Secrets blocklist

The publish gate blocks output containing patterns that look like credentials. Default patterns catch:

- OpenAI API keys (`sk-...`)
- Anthropic API keys (`sk-ant-...`)
- Bearer tokens
- PEM private keys

Add custom patterns at runtime by inserting into the `secrets_blocklist` table:

```sql
INSERT INTO secrets_blocklist(pattern) VALUES('MY_CUSTOM_SECRET_\d+');
```

## Testing

Run the full test suite:

```bash
pip install -r proxy_agent/requirements.txt
python -m pytest tests/ -v
```

The tests use an isolated temporary SQLite database per test (via `tmp_path`), so no cleanup is needed and tests can run in parallel. All LLM calls are mocked -- no API keys or network access required.

### Test coverage

| File | Tests | Covers |
|---|---|---|
| `test_llms.py` | 18 | All three backends, `route_call` routing, env var config |
| `test_publish_gate.py` | 10 | Default patterns, Anthropic keys, DB-driven patterns |
| `test_memory.py` | 10 | Event append/retrieval, summary CRUD, ordering |
| `test_db.py` | 5 | Schema creation, idempotency, row factory |
| `test_voice.py` | 3 | Canonicalization delegation and prompt construction |
| `test_moltbook.py` | 5 | Auth headers, post creation, error handling |
| `test_app.py` | 8 | `/draft` endpoint, secret blocking, validation, startup |

## Docker

Build and run:

```bash
docker build -t indy-the-agent .
docker run -d --name indy-the-agent -p 8000:8000 --env-file .env indy-the-agent
```

Or use the deploy script, which handles building, stopping any existing container, and starting fresh:

```bash
./scripts/deploy.sh
```

The deploy script reads from the following environment variables:

| Variable | Default | Description |
|---|---|---|
| `IMAGE_NAME` | `indy-the-agent` | Docker image name |
| `CONTAINER_NAME` | `indy-the-agent` | Container name |
| `PORT` | `8000` | Host port to bind |
| `ENV_FILE` | `.env` | Path to env file with LLM keys |

## Moltbook stub

The Moltbook tool is a stub until you wire actual endpoints from `moltbook.com/skill.md`. Update
`proxy_agent/moltbook.py` and then uncomment the publish block in `proxy_agent/app.py`.
