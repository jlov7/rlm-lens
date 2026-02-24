# Security & Privacy — RLM-Lens

## 1. Data handling
- RLM-Lens is **local-first**:
  - Index and traces are stored on disk in `./.rlm-lens/`
  - Server binds to `127.0.0.1` by default
- External data egress:
  - Only data sent externally is what the runtime includes in prompts to the chosen LLM provider.
  - The corpus is not uploaded wholesale; it is accessed via search/read operations.
- Supported providers include native labs and gateways:
  - Native: OpenAI, Anthropic, Gemini, xAI
  - OpenAI-compatible gateways: OpenRouter, Together, Groq, Fireworks

## 2. Key risks
1. **Path traversal / arbitrary file reads**
2. **Secret leakage into traces**
3. **Executing arbitrary code in Local REPL**
4. **Accidentally indexing sensitive directories**

## 3. Mitigations (required)
### 3.1 Filesystem safety
- Normalize all paths.
- Resolve realpath and enforce that any read is within `corpus_root`.
- Explicit denylist:
  - `.git/`, `node_modules/`, `.env`, `**/*secret*`, `**/*key*` (configurable)
- Default exclude hidden folders unless explicitly enabled.

### 3.2 Secret redaction
- Before persisting trace events, run redaction on:
  - API keys (common patterns)
  - PEM blocks
  - `OPENAI_API_KEY=...` style
- Store redaction markers rather than original values.

### 3.3 Hosted BYOK controls
- Session-key flow is supported through request header `X-RLM-LENS-PROVIDER-KEY`.
- Session key is used for the run invocation only and is **not** stored in run config/database.
- UI keeps session key in memory only (not project files / not exported traces).
- For strongest trust, users can self-host backend and set keys via local env.

### 3.4 Sandbox isolation
- Default to Docker REPL (isolated) when available.
- Local REPL is allowed only with a clear UI warning.

### 3.5 Networking
- No inbound external access by default.
- If user opts into LAN binding, show warning and require explicit flag.

## 4. Operational guidance
- Do not index directories containing regulated data unless approved.
- Prefer using a proxy/gateway key with limited permissions.
