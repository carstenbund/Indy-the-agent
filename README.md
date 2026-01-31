# Indy-the-agent

Minimal identity-proxy scaffold for a single-voice agent with pluggable LLM backends and durable memory.

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

## Environment configuration

Set backends per purpose (`openai_compat`, `ollama`, or `claude`):

```bash
export LLM_DRAFT_BACKEND=claude
export LLM_DRAFT_MODEL=claude-sonnet-4-20250514
export LLM_VOICE_BACKEND=claude
export LLM_VOICE_MODEL=claude-sonnet-4-20250514
export LLM_SUMMARIZE_BACKEND=ollama
export LLM_SUMMARIZE_MODEL=llama3.1
```

OpenAI-compatible routing uses:

```bash
export OPENAI_COMPAT_BASE_URL=https://api.openai.com/v1
export OPENAI_API_KEY=sk-...
```

Claude (Anthropic) routing uses:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_BASE_URL=https://api.anthropic.com   # optional, defaults to this
```

You can also set per-purpose max tokens for Claude:

```bash
export LLM_DRAFT_MAX_TOKENS=4096
export LLM_VOICE_MAX_TOKENS=4096
```

Ollama routing uses:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
```

## Moltbook stub

The Moltbook tool is a stub until you wire actual endpoints from `moltbook.com/skill.md`. Update
`proxy_agent/moltbook.py` and then uncomment the publish block in `proxy_agent/app.py`.
