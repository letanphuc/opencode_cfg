---
name: cls-review
description: Review Gerrit CLs (changes). Workflow: fetch CL details, download patch, link Jira ticket context, analyze base source, post review comments and votes. Uses gerrit skill (gr.sh) and atlassian-cli skill (acli).
---

# CLs Review

Review Gerrit changes end-to-end: pull context from Gerrit + Jira, analyze the diff against the workspace base source, and post review comments with votes.

## Dependencies

- **gerrit** skill — `gr.sh` for `get`, `patch`, `review`
- **atlassian-cli** skill — `acli` for Jira ticket lookup
- Workspace source tree (for base source comparison)

## Workflow

### 1. Fetch CL Details

```bash
gr.sh get 6377
```

Extract: title, project, branch, patchset, and the Jira ticket key from the subject (e.g. `[AW-2030]`).

### 2. Download Patch

```bash
gr.sh patch 6377 -d /tmp/opencode/
```

Read the patch to understand the diff context (files changed, lines, nature of change).

### 3. Pull Jira Context

Use `acli` to fetch the linked ticket. Jira key is usually in the commit subject (e.g. `[AW-2030]`):

```bash
acli jira workitem view AW-2030 --json
```

Focus on the **description** field — it often contains root cause analysis, logs, or reproduction steps that inform the review.

### 4. Analyze Base Source

Locate the affected file(s) in the workspace and read the surrounding context:

```bash
# Find the file
find <workspace> -path "*/<project>/<file>" 2>/dev/null
```

When reviewing config changes (like `.conf`, `.mk`, `Android.bp`):
- Check neighboring variants (e.g. SR200 vs SR1XX configs) for consistency
- Look for comments that describe the expected value
- Search for related constants/defines in headers (e.g. `UCI_EXT_PARAM_DPD_WAKEUP_SRC`)
- Verify the change matches the problem described in the Jira ticket

### 5. Post Review

```bash
gr.sh review <change> -m "<comment>" --code-review <vote>
```

Vote options:
- `+2` — approved
- `+1` — looks good (minor suggestions optional)
- `-1` — needs changes (explain why)
- `-2` — do not merge (critical issues)

```bash
# With verified vote as well
gr.sh review 6377 --code-review +2 --verified +1 -m "LGTM"
```

### Review Checklist

- [ ] Does the change address the Jira ticket's described problem?
- [ ] Is it the minimal change needed, or is there a broader fix?
- [ ] Are sibling/neighboring configs consistent (e.g. other chip variants)?
- [ ] Do inline comments/docs match the new value?
- [ ] Are there related constants/defines in headers that corroborate the change?
- [ ] Any risk of regression for other variants or configurations?

## Tips

- Prefer `+1` with notes over `+2` unless you're fully confident — leaves room for the author to consider feedback
- If the Jira ticket isn't linked in the commit subject, check Gerrit's topic or description
- For multi-file CLs, read each file's surrounding context, not just the diff hunks
- Save key observations to kratos-memory for future sessions
