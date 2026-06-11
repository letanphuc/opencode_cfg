---
name: push-cl
description: Push local commits to Gerrit for review. Handles project creation, branch bootstrapping, Change-Id insertion, and rebase-on-detached scenarios.
---

# Push CL to Gerrit

Push a local commit from a repo-managed project to Gerrit for code review.

## Quick Reference

```bash
git -C <project_path> push ohd HEAD:refs/for/<target_branch>
```

## Common Pattern

When the user provides a markdown table of CLs (e.g. `doc/nfc-cls.md`), extract each project path and push each one.

## Prerequisites

- The project must be a git repo
- SSH access to Gerrit configured
- The `commit-msg` hook installed in the repo (download from `https://gerrit.mijo.services/tools/hooks/commit-msg`)

## Full Workflow

### Step 1: Look up the Gerrit project name

Use `repo list` to get the Gerrit project name from the local path:

```bash
repo list <project_path>
# Output: <local_path> : <gerrit_project_name>
```

If `repo list` doesn't know the project (new project not in manifest), infer the naming convention from existing projects in the same parent directory. Common patterns:

| Local path | Gerrit project name |
|---|---|
| `packages/apps/*` | `platform/packages/apps/*` |
| `packages/modules/*` | `platform/packages/modules/*` |
| `vendor/*` | `platform/vendor/*` |
| `device/qcom/monaco` | `device/qcom/monaco_device` |
| `device/qcom/common/monaco` | `device/qcom/monaco/common` |

### Step 2: Ensure the remote exists

Check if the `ohd` remote exists:

```bash
git -C <project_path> remote get-url ohd
```

If missing, add it:

```bash
git -C <project_path> remote add ohd ssh://gerrit-ssh.mijo.services:29418/<gerrit_project_name>
```

### Step 3: Ensure the Gerrit project exists

Try to push. If the push fails with:

```
fatal: project <name> not found
```

Create the project via SSH:

```bash
ssh -p 29418 <user>@gerrit-ssh.mijo.services gerrit create-project <gerrit_project_name>
```

Then retry the push.

### Step 4: Ensure the target branch exists on Gerrit

If the push fails with:

```
[remote rejected] HEAD -> refs/for/<branch> (branch <branch> not found)
```

The target branch does not exist in this repository yet. Bootstrap it by creating an orphan branch locally and force-pushing it to `refs/heads/<branch>`:

```bash
cd <project_path>
git checkout --orphan temp-orphan
git rm -rf .
git commit --allow-empty -m "init <branch> branch"
git push ohd temp-orphan:refs/heads/<branch> -f
git checkout <original_branch>
git branch -D temp-orphan
```

Then rebase the target commit onto the new branch and push for review:

```bash
git fetch ohd <branch>
git checkout -b <branch> ohd/<branch>
git cherry-pick <commit_hash>
git push ohd HEAD:refs/for/<branch>
```

### Step 5: Install the commit-msg hook

If the push fails with:

```
missing Change-Id in message footer
```

Download and install the hook, then amend the commit:

```bash
cd <project_path>
HOOK="$(git rev-parse --git-dir)/hooks/commit-msg"
curl -o "$HOOK" https://gerrit.mijo.services/tools/hooks/commit-msg
chmod +x "$HOOK"
git commit --amend --no-edit
git push ohd HEAD:refs/for/<branch>
```

### Step 6: Handle "no new changes"

If the push fails with:

```
[remote rejected] HEAD -> refs/for/<branch> (no new changes)
```

The commit is already reachable from the target branch. Rebase it onto the current branch tip:

```bash
cd <project_path>
git fetch ohd <branch>
git checkout -b <branch>-push ohd/<branch>
git cherry-pick <commit_hash>
# install hook, amend, push as in Step 5
```

If the commit has no common ancestry with the target branch:

```
[remote rejected] HEAD -> refs/for/<branch> (no common ancestry)
```

Use `cherry-pick` to rebase the commit onto an orphan-init branch as shown in Step 4.

## Pushing Multiple CLs from a Markdown Table

When given a markdown file with a CL table:

1. Parse the table to extract `project_path` and `commit_hash` for each row
2. For each CL, follow the workflow above
3. Report results in a summary table with `[change_number](url)` links

## After Pushing

Restore the original branch:

```bash
git checkout <original_branch>
git branch -D <temp_branch>
```

## Gerrit Host Details

- SSH host: `gerrit-ssh.mijo.services:29418`
- Web URL: `https://gerrit.mijo.services/c/<project>/+/<change_number>`
- Hook URL: `https://gerrit.mijo.services/tools/hooks/commit-msg`
