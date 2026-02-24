# Trace Format — RLM-Lens

RLM-Lens stores traces in two forms:
1. **JSONL file per run** (append-only), designed to be compatible with the `rlms` library trajectory format.
2. **SQLite trace_events** for UI queries and filtering.

## 1. JSONL conventions
- One JSON object per line.
- Each object has:
  - `type`: `"metadata"` or `"iteration"` (compatible with rlms `RLMLogger`)
  - `timestamp`: ISO8601
- RLM-Lens may optionally add additional event types (prefixed) but should keep core compatibility.

## 2. Event types

### 2.1 `metadata`
Shape:
```json
{
  "type": "metadata",
  "timestamp": "2026-02-23T12:34:56.000Z",
  "root_model": "gpt-5-nano",
  "max_depth": 2,
  "max_iterations": 10,
  "backend": "openai",
  "backend_kwargs": { "model_name": "gpt-5-nano" },
  "environment_type": "docker",
  "environment_kwargs": { "image": "python:3.12-slim" },
  "other_backends": null
}
```

### 2.2 `iteration`
Shape:
```json
{
  "type": "iteration",
  "iteration": 1,
  "timestamp": "2026-02-23T12:34:58.000Z",
  "prompt": "...",
  "response": "...",
  "code_blocks": [
    {
      "code": "lens.search('retry policy')",
      "result": {
        "stdout": "",
        "stderr": "",
        "locals": { "hits": "..." },
        "execution_time": 0.12,
        "rlm_calls": [
          {
            "root_model": "gpt-5-nano",
            "prompt": "...",
            "response": "...",
            "usage_summary": {
              "model_usage_summaries": {
                "gpt-5-nano": {
                  "total_calls": 1,
                  "total_input_tokens": 123,
                  "total_output_tokens": 456,
                  "total_cost": 0.0012
                }
              },
              "total_cost": 0.0012
            },
            "execution_time": 1.23
          }
        ],
        "final_answer": null
      }
    }
  ],
  "final_answer": null,
  "iteration_time": 4.2
}
```

Notes:
- `locals` is a serialized representation of REPL locals.
- `rlm_calls` is a list of subcalls executed during the code block.

## 3. Streaming events to the UI
For live UI updates, the backend can stream:
- identical `metadata` and `iteration` events
- plus optional lightweight events:
  - `budget` updates
  - `status` updates

If extra event types are used in streams, keep the persisted JSONL strictly compatible (or store extras only in DB).

## 4. Trace → UI mapping
UI should derive:
- Graph nodes from:
  - each iteration
  - each code block
  - each subcall
- Node edges represent parent-child relationships:
  - iteration → code block → subcall

## 5. Export bundle contract
Export must include:
- `trace.jsonl` (this format)
- `run.json` (run config + summary)
- `citations.json`
- `answer.md`
- `corpus_manifest.json`

