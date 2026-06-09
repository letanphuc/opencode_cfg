---
name: kratos-memory
description: Use npx kratos-memory CLI for persistent memory across sessions. Search before starting work, save observations as you go. Use ONLY for managing memories — save, search, ask, recent, get, forget, status, scan, summary, export, pin.
---

# Kratos Memory — Persistent memory for opencode

Use `npx kratos-memory` for persistent, searchable memory that survives across sessions. All data stored locally in `~/.kratos/` — SQLite + FTS5, zero network calls.

## Workflow

1. **Before starting any task**: Run `npx kratos-memory search "<query>"` to recall relevant context from past sessions.
2. **After learning something important**: Run `npx kratos-memory save "<observation>" --tags <tag1,tag2>` to persist it.
3. **Periodically check**: Run `npx kratos-memory status` to see memory stats.

## Commands

| Command | Usage |
|---------|-------|
| `save <text>` | Save a memory. Options: `--tags tag1,tag2` `--importance 1-5` `--paths file.ts` `--json` |
| `search <query>` | Full-text search. Options: `--limit N` `--tags t1,t2` `--json` |
| `ask <question>` | Natural language query. Options: `--json` |
| `recent` | Recent memories. Options: `--limit N` `--json` |
| `get <id>` | Full memory details. Options: `--json` |
| `forget <id>` | Delete a memory. Options: `--json` |
| `update <id> <text>` | Update a memory. Options: `--tags` `--importance` `--paths` `--json` |
| `pin <id>` | Pin a memory so it always surfaces first. |
| `status` | System dashboard. Options: `--json` |
| `export` | Export all memories as JSON. |
| `summary` | Generate a project summary from all memories. |
| `scan <text>` | Detect PII and secrets. Options: `--redact` `--json` |
| `hooks install` | Install auto-capture hooks for Claude Code sessions. |
| `switch <project>` | Switch to a different project scope. |

## When to save

- Architecture decisions (why you chose X over Y)
- Discovered patterns or conventions in the codebase
- Bug root causes and fixes
- User preferences or constraints
- API endpoints, auth patterns, environment setup
- Any context that would be costly to rediscover

Use meaningful tags: `architecture`, `auth`, `bug`, `config`, `api`, `database`, `frontend`, `deployment`, `convention`, etc.

## Storage

- `~/.kratos/projects/` — per-project SQLite databases
- Automatically detects project from cwd
- Use `npx kratos-memory switch <path>` to change project scope
- Add `--global` flag to any command for cross-project memory
