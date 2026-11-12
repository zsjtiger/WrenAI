# Model endpoints for janus

Two optional model services, both OpenAI-compatible:

| Use | Variables | Example |
|---|---|---|
| Embeddings (semantic recall, FK tie-break) | `JANUS_EMBEDDING_BACKEND=api`, `JANUS_EMBEDDING_API_BASE_URL`, `JANUS_EMBEDDING_API_MODEL`, optional `JANUS_EMBEDDING_API_KEY` | qwen3-embedding-4b at `http://8.130.170.41:8081/v1` |
| Chat (`--suggest-terms`, `--refine-with-model`, `--confirm-with-model`) | `JANUS_LLM_BASE_URL`, `JANUS_LLM_MODEL`, `JANUS_LLM_API_KEY` | DeepSeek at `https://api.deepseek.com`, model `deepseek-v4-pro` or `deepseek-flash` |

## Setup

```bash
cp .env.example .env        # .env is git-ignored; fill in JANUS_LLM_API_KEY
python check_endpoints.py   # checks both endpoints; never prints a key
```

Keys belong in `.env` or your shell environment, never in a project file or a commit.

## Use with janus

```bash
janus context terms --refine-with-model
janus context attributes --refine-with-model
janus context infer-fks --confirm-with-model
janus context draft --from-db --suggest-terms
```

Each model step falls back to rule results when the model is unreachable.
