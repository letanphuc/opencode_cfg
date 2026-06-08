---
name: gerrit
description: Gerrit code review via SSH. Query changes, search by author/reviewer/label/branch/path, download patches, apply changes locally, reset workspaces. Uses gertool CLI with isolated venv.
---

# Gerrit Integration

Use the `gr.sh` wrapper to interact with Gerrit. The full path is:

    ~/.config/opencode/skills/gerrit/gr.sh

## Configuration

Credentials are hardcoded in `gr.sh`. To change them, edit the file:

```bash
export GERRIT_USER=your-ssh-username
export GERRIT_HOST=gerrit-ssh.example.com
```

Alternatively, pass `--user` / `--host` on every command.

## Commands

### `patch` — Download patch file (no git repo needed)

Downloads a Gerrit patch file as a `.patch` via REST API. Queries change metadata by SSH, then fetches the patch over HTTPS. No git repo required.

Single change (auto-named file):
```bash
gr.sh patch 12345
```

Save to a directory:
```bash
gr.sh patch 12345 -d ./patches/
```

Custom output filename:
```bash
gr.sh patch 12345 -o my-fix.patch
```

All patches in a topic:
```bash
gr.sh patch my-topic -t -d ./topic-patches/
```

### `get` — Fetch change details

By change number (prints download commands):
```bash
gr.sh get 12345
```

By topic (lists all changes):
```bash
gr.sh get my-topic
```

### `search` — Search changes with filters

All flags optional, defaults to `status:open` if no filters given.

**Basic filters:**
```bash
gr.sh search --author "alice@example.com"
gr.sh search --reviewer "bob" --status open
gr.sh search --label "Code-Review=2" --branch main
gr.sh search --project "my/repo" --limit 10
gr.sh search --message "fix crash"
```

**Extended filters:**
```bash
gr.sh search --path "src/main.c" --branch main
gr.sh search --comment "TODO" --status open
gr.sh search --age 7d --status open
gr.sh search --after "2024-06-01" --before "2024-07-01"
gr.sh search --is starred --status open
gr.sh search --has draft --status open
gr.sh search --has unresolved --reviewer "bob"
```

**Project glob (wildcard expansion):**
```bash
gr.sh search --project "chipcode/sw5100-*_standard_oem" --status open
gr.sh search --project "rtos-platform/*" --project "chipcode/*" --status open
```

**Raw query (maximum flexibility):**
```bash
gr.sh search --query "status:open AND branch:main AND -age:7d"
gr.sh search --query "owner:self AND is:starred limit:20"
```

**Fetch all results (paginates automatically):**
```bash
gr.sh search --project "chipcode/sw5100-*_standard_oem" --all
```

| Flag | Gerrit operator | Example |
|------|----------------|---------|
| `--author` | `owner:` | `--author "john"` |
| `--reviewer` | `reviewer:` | `--reviewer "jane@ex.com"` |
| `--label` | `label:` | `--label "Code-Review=2"` |
| `--branch` | `branch:` | `--branch "main"` |
| `--project` | `project:` | `--project "my/repo"` or glob `--project "chipcode/*"` (repeatable) |
| `--status` | `status:` | `--status "open"` |
| `--topic` | `topic:` | `--topic "my-feature"` |
| `--message` | `message:` | `--message "crash fix"` |
| `--comment` | `comment:` | `--comment "TODO"` |
| `--path` | `path:` | `--path "src/main.c"` |
| `--age` | `age:` | `--age "7d"` |
| `--after` | `after:` | `--after "2024-01-01"` |
| `--before` | `before:` | `--before "2024-12-31"` |
| `--is` | `is:` | `--is "starred"` |
| `--has` | `has:` | `--has "draft"` |
| `--query` | raw query | `--query "status:open owner:self"` |
| `--limit` | `limit:` | `--limit 25` |
| `--all` | fetch all | paginates to get every result |

### `diff` — Download diff via REST API

```bash
gr.sh diff 12345
gr.sh diff 12345 -o changes.patch
```

### `reset-to` — Apply changes to local repos

Resolves Gerrit project → local path via `west list`. Fetches + checkouts (or pulls).

```bash
gr.sh reset-to 12345
gr.sh reset-to my-topic --mode checkout
gr.sh reset-to 12345 --mode pull
gr.sh reset-to 12345 --dry-run
```

### `reset-all` — Reset entire workspace

Runs `west forall -c 'git reset --hard'`, pulls `mijo/manifest`, then `west update`.

```bash
gr.sh reset-all
gr.sh reset-all --dry-run
```

## Dependencies

Uses its own venv: `~/.config/opencode/skills/gerrit/venv/` (loguru pre-installed).

To install additional deps:
```bash
~/.config/opencode/skills/gerrit/venv/bin/pip install <package>
```
