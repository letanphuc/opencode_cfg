---
name: refine-cl
description: Refine an existing Gerrit CL — view changes, edit locally, amend commit, push new patchset. Covers the full update loop for in-flight changes.
---

# Refine CL

Iterate on an existing Gerrit change: inspect, edit, re-commit, and push a new patchset.

## Important: Always Work in the Repo Directory

All git commands (fetch, checkout, add, commit, amend, push) **must** run inside the specific project's repo directory — never from the workspace root. For example:

```bash
cd /workspace/wear/pdk/packages/apps/NfcTagEmulator
git add -A && git commit --amend --no-edit
git push ohd HEAD:refs/for/mijo_dev
```

Use `gr.sh reset-to <change_number>` to automatically cd into the correct repo, or use `git -C <project_path>` for one-off commands. Use the `Bash` tool's `workdir` parameter — never `cd <path> && <command>`.

## Dependencies

- `gr.sh` (gerrit skill) for fetching CL details
- `push-cl` skill for initial push workflows (hook setup, branch bootstrapping)
- SSH access to `gerrit-ssh.mijo.services:29418`

## Workflow Overview

```
  View  →  Reset-to  →  Edit  →  Amend  →  Push
```

Each step is detailed below.

## Step 1: View CL Changes

### Metadata

```bash
gr.sh get <change_number>
```

Shows title, branch, project, patchset count, and download commands.

### Diff (content review)

```bash
gr.sh diff <change_number>                   # stdout
gr.sh diff <change_number> -o changes.patch  # save to file
```

### Changed files

```bash
gr.sh get <change_number>
# Use the "Checkout" git command to inspect the commit:
cd <project_path>
git show FETCH_HEAD --stat
git diff FETCH_HEAD^1..FETCH_HEAD
```

Or read the files directly after reset-to (Step 2).

## Step 2: Apply CL Locally

```bash
gr.sh reset-to <change_number>
```

This fetches the latest patchset and checks it out as detached HEAD in the correct local repo (maps Gerrit project → local path automatically).

If the project is not tracked by `repo` (e.g. a new project), `reset-to` will warn and skip. Work around it:

```bash
cd <project_path>
git fetch ssh://gale@gerrit-ssh.mijo.services:29418/<gerrit_project> \
  refs/changes/<last2>/<number>/<patchset> && git checkout FETCH_HEAD
```

- `<last2>` = last 2 digits of the change number (e.g. `09` for `6409`)
- `<patchset>` = patchset number from `gr.sh get`

## Step 3: Edit

Make code changes in the checked-out state. The working tree is at detached HEAD with the CL's commit applied.

Use glob, grep, read, and edit tools to locate and modify the relevant files.

Verify the changes with:
```bash
git diff
```

## Step 4: Re-commit

Amend the existing commit to preserve the Change-Id:

```bash
cd <project_path>

# Ensure commit-msg hook is installed
HOOK="$(git rev-parse --git-dir)/hooks/commit-msg"
[ -x "$HOOK" ] || curl -o "$HOOK" https://gerrit.mijo.services/tools/hooks/commit-msg && chmod +x "$HOOK"

git add -A
git commit --amend --no-edit  # preserves commit message + Change-Id
```

Use `--amend` — **never** create a new commit. The Change-Id in the footer tells Gerrit this is a new patchset on the same change.

### Updating the commit message

If the commit message needs changes too:

```bash
git commit --amend          # opens editor (or use -m)
```

The hook will re-insert or preserve the Change-Id footer.

## Step 5: Push New Patchset

```bash
cd <project_path>
git push ohd HEAD:refs/for/<target_branch>
```

The target branch is shown in `gr.sh get` output (the `Branch:` field).

### With a topic

If the CL belongs to a topic (set via `gr.sh get`):

```bash
git push ohd HEAD:refs/for/<target_branch>%topic=<topic_name>
```

### If the remote is missing

```bash
git remote add ohd ssh://gerrit-ssh.mijo.services:29418/<gerrit_project>
```

Find `<gerrit_project>` via `gr.sh get` or `repo list <project_path>`.

## Step 6: Verify

After pushing, `gr.sh get` will show the updated patchset number:

```bash
gr.sh get <change_number>
```

Confirm the new patchset is visible and the diff reflects your changes.

## Troubleshooting

| Error | Fix |
|---|---|
| `no new changes` | The amended commit is identical to the current patchset. Ensure you actually changed something. |
| `missing Change-Id` | Install the commit-msg hook, re-run `git commit --amend --no-edit`. |
| `branch not found` | See `push-cl` skill — bootstrap the branch on Gerrit first. |
| `project not found` | See `push-cl` skill — create the project on Gerrit first. |
| `reset-to` skips project | Work around with manual fetch + checkout (Step 2). |
| Working tree dirty on reset-to | Stash or discard changes first: `git stash` or `git checkout -- .` |

## Quick Ref: Full Cycle

```bash
# View
gr.sh get 6409
gr.sh diff 6409

# Apply
gr.sh reset-to 6409

# Edit (use file tools)

# Amend + push
git add -A
git commit --amend --no-edit
git push ohd HEAD:refs/for/mijo_dev
```

## Gerrit Host Details

| Item | Value |
|---|---|
| SSH host | `gerrit-ssh.mijo.services:29418` |
| Web URL | `https://gerrit.mijo.services/c/<project>/+/<change_number>` |
| Hook URL | `https://gerrit.mijo.services/tools/hooks/commit-msg` |
| Remote name | `ohd` |
