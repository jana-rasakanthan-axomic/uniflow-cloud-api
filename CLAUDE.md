# UniFlow Cloud API (uniflow-cloud-api)

Python/FastAPI cloud broker on AWS Fargate. Mediates between edge agents (Rust/Tauri) and the web portal (React).

## Context Loading

Before running `/design`, `/plan`, or `/build` in this repo, load workspace context:
1. Read `../CLAUDE.md` for workspace structure and shorthand reference
2. Read `../.claude/topic-index.md` for cross-repo doc discovery
3. Read the relevant epic's `*-rules.md` for business rules and its `## References` table
4. Follow `## References` paths to load upstream docs (PRDs, ADRs, schemas)

## Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL
- **Deployment:** AWS Fargate (Docker)
- **Test runner:** pytest
- **Linter:** ruff

## Source Layout

```
app/
  api/          # Route handlers (3 router groups)
  models/       # SQLAlchemy models
  services/     # Business logic
  config.py     # Settings and env
  main.py       # FastAPI app entry point
tests/          # pytest test suite
```

## Router Groups

| Group | Prefix | Purpose |
|-------|--------|---------|
| Auth | `/api/v1/auth/` | OAuth/PKCE, JWT tokens, device linking |
| Web | `/api/v1/` | Portal-facing: search, collections, jobs, devices |
| Edge | `/api/v1/edge/` | Agent-facing: signaling, upload, sync |

## Component-to-Doc Mapping

| Component | Upstream Docs | Epic |
|-----------|--------------|------|
| Auth & JWT tokens | N7, doc-23, N18-adr | ep01, ep02 |
| Device registration | doc-06 §2, N5 §2.2 | ep02 |
| PostgreSQL schema | doc-25, doc-08 | ep01 |
| Job state machine | N8, doc-01 §3 | ep01 |
| Long-poll signaling | doc-12, doc-28 | ep01 |
| REST API contract | doc-27, doc-30 | ep01 |
| Search (FTS) | N10, doc-03 | ep04 |
| Digital twin ingest | N9, doc-08 | ep03 |
| STS credential issuance | doc-16 | ep07 |
| OA pre-registration | doc-18, doc-10 | ep07 |
| OA finalization | doc-10 | ep07 |
| Upload hash verification | doc-20 | ep07 |
| Collections & tagging | doc-07, doc-10 | ep06 |
| Fleet management | doc-06 §4-5, N6 | ep09 |
| Audit log | N6 §3, doc-25 | ep09 |

## Workspace Docs

All doc shorthand codes (N1-N18, doc-01 to doc-30, App-A to App-E) resolve via `../CLAUDE.md` shorthand table. Full PRD docs are in `../uniflow-docs/`. Epic designs are in `../.claude/active/epNN/design/`.

## Workspace ADRs

- `../docs/adr/0001-long-poll-signaling.md`
- `../docs/adr/0002-job-state-machine-enforcement.md`
- `../docs/adr/0003-per-instance-oa-api-semaphore.md`

## TDD Contract

- `../docs/design/platform-foundation.md` — EP-01 technical design with layer contracts
