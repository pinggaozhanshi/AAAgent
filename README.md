# AAAgent

> A local-first AI agent workbench for building, observing, and debugging structured AI workflows.

AAAgent turns a normal LLM conversation into an inspectable local run: choose OpenAI-compatible model profiles, generate a task DAG, watch dependent tasks execute, and inspect token usage, outputs, and failures from one workspace.

## Why AAAgent

Most chat interfaces hide how an agent reached its answer. AAAgent is being built for developers and learners who want an agent that is easier to understand and evolve:

- **Local-first runtime**: the UI and FastAPI service run on your machine.
- **OpenAI-compatible providers**: use DeepSeek, OpenAI, Kimi, Ollama, or compatible endpoints.
- **Professional mode**: plan a request as a DAG, render it as a live graph, and inspect each task.
- **Persistent run history**: SQLite records sessions, profiles, runs, tasks, dependencies, artifacts, and usage.
- **Safe-by-default profiles**: API keys are kept only in the active local service memory; SQLite stores metadata and credential references, never raw keys.
- **Readable agent behavior**: the planner must return compact JSON, which is locally validated before it reaches the scheduler.

## Current Capabilities

`v0.1.3` is a working local prototype with:

- Casual and professional interaction modes
- Saved planner/executor model profiles, up to 10 active profiles
- OpenAI-compatible chat completion calls
- DeepSeek JSON-output planning support
- JSON TaskGraph validation: duplicate IDs, bad dependencies, and cycles are rejected
- DAG scheduling with dependency-aware bounded concurrency
- Live task states: planned, ready, running, completed, failed, blocked, and cancelled
- Graph canvas with directional dependency arrows and task inspection
- Provider-reported token usage timeline when usage data is available
- Same-origin Node proxy that launches and supervises the local FastAPI service
- A Windows one-click launcher

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+

### Windows: one click

Double-click [AAAgent-Run.bat](./AAAgent-Run.bat).

### Manual start

```bash
npm install
pip install -r backend/requirements.txt
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Node entrypoint starts and proxies the local FastAPI service automatically, so the browser only needs one local origin.

## Using Professional Mode

1. Open **Settings** and create a model profile.
2. Enter a provider, base URL, model name, and API key.
3. Choose the profile as both the **Planner** and **Executor**, or create separate profiles for each role.
4. Send a multi-step request.
5. Select **View Task Graph** to inspect dependencies, task state, duration, and output summaries.

For DeepSeek's OpenAI-compatible API:

```text
Base URL: https://api.deepseek.com
Model:    deepseek-v4-pro
```

A planning profile with a lower temperature, such as `0.2` to `0.4`, is recommended. Keep the execution profile around `0.7` when you want more expansive answers.

## Architecture

```text
Browser UI
  │ same-origin /api
  ▼
Node.js local entrypoint (port 5173)
  ├─ serves src/ui
  ├─ supervises FastAPI
  └─ proxies /api requests
       ▼
FastAPI local service (port 8000)
  ├─ model profiles and runtime-only keys
  ├─ planner prompt and JSON TaskGraph validation
  ├─ DAG scheduler and SSE events
  └─ SQLite repository
       ▼
OpenAI-compatible model providers
```

## Repository Layout

```text
AAAgent/
├── backend/
│   ├── database.py          # SQLite connection and initialization
│   ├── schema.sql           # v0.1.3 database schema
│   ├── prompts.py           # Planner and executor prompts
│   ├── professional.py      # Profiles, planning, DAG execution, events
│   └── sse_server.py        # FastAPI application
├── src/ui/                  # Local web UI
├── docs/                    # Design decisions and SQLite guide
├── server.cjs               # Node entrypoint and API proxy
└── AAAgent-Run.bat          # Windows launcher
```

## Design Notes

The task graph is deliberately not generated from free-form Markdown. The planning model must output a compact JSON graph with explicit task IDs and `dependsOn` relationships. AAAgent validates the graph locally, persists it, then renders it as a DAG.

When a planning response is malformed or unavailable, AAAgent falls back to a deterministic local DAG for common implementation requests: analysis branches into frontend and backend work, then converges on verification and delivery.

## Roadmap

- [x] Local chat and OpenAI-compatible profiles
- [x] SQLite-backed runs, usage records, and task artifacts
- [x] Professional-mode DAG planning and visualization
- [ ] Electron desktop shell and secure OS credential storage
- [ ] MCP tools with approval policies
- [ ] File, image, and URL inputs
- [ ] Long-term memory and local retrieval
- [ ] Evaluation datasets and run replay

## Documentation

- [Software Design v0.1.1](./docs/SDD-v0.1.1.md)
- [Frontend and Delivery Design v0.1.2](./docs/SDD-v0.1.2.md)
- [Professional Mode Design v0.1.3](./docs/SDD-v0.1.3.md)
- [SQLite Guide v0.1.3](./docs/SQLITE-v0.1.3.md)

## Contributing

Issues and pull requests are welcome. The most useful contributions right now are provider adapters, deterministic TaskGraph tests, UI accessibility improvements, and persistence/migration hardening.

## License

MIT