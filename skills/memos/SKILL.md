---
name: memos
description: Use when the user mentions "memos", "memos app", "note-taking", or wants to create/read/update/delete notes via a Memos instance. Provides an MCP server that wraps the full Memos API (memos, comments, attachments, reactions, shares, users, instance).
---

# Memos Integration

Memos is an open-source, self-hosted note-taking app. This skill provides an MCP server that exposes the Memos API as tools.

## Configuration

Set these environment variables in your shell profile or opencode config:

| Variable | Description |
|----------|-------------|
| `MEMOS_URL` | Your Memos instance URL (default: `http://localhost:5230`) |
| `MEMOS_TOKEN` | Your Memos API access token (from Settings → Access Tokens) |

## Available MCP Tools

### Memos CRUD
- `memos_list` — List memos with filters, ordering, pagination
- `memos_get` — Get a single memo by ID
- `memos_create` — Create a new memo (Markdown content, visibility, state)
- `memos_update` — Update a memo (requires `updateMask`)
- `memos_delete` — Delete a memo permanently

### Comments
- `memos_comments_list` — List comments on a memo
- `memos_comment_create` — Create a comment on a memo

### Attachments
- `memos_attachments_list` — List attachments for a memo

### Relations
- `memos_relations_list` — List memo relations
- `memos_relations_set` — Set memo relations

### Reactions
- `memos_reactions_list` — List reactions
- `memos_reaction_upsert` — Add/update a reaction
- `memos_reaction_delete` — Remove a reaction

### Shares
- `memos_shares_list` — List share links
- `memos_share_create` — Create a share link
- `memos_share_delete` — Delete a share link

### Users
- `memos_users_list` — List users (admin)
- `memos_user_get` — Get user details

### Instance
- `memos_profile` — Get instance profile (version, admin, settings)

## Visibility Levels

| Level | Description |
|-------|-------------|
| `PRIVATE` | Only the creator can see |
| `PROTECTED` | Authenticated users can see |
| `PUBLIC` | Anyone can see (including anonymous) |

## Example Workflows

**Quick note capture:**
```
memos_create content="Remember to buy groceries: milk, eggs, bread"
```

**Search recent memos:**
```
memos_list orderBy="create_time desc" pageSize=5
```

**Update visibility of a memo:**
```
memos_update memo="1" updateMask="visibility,content" content="Updated content" visibility="PUBLIC"
```

**Archive a memo:**
```
memos_update memo="1" updateMask="state" state="ARCHIVED"
```

## Memo Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Resource name (`memos/{id}`) |
| `content` | string | Markdown content |
| `visibility` | enum | `PRIVATE`, `PROTECTED`, `PUBLIC` |
| `state` | enum | `NORMAL`, `ARCHIVED` |
| `pinned` | boolean | Whether pinned |
| `tags` | string[] | Tags |
| `creator` | string | Creator resource name |
| `createTime` | string | RFC 3339 timestamp |
| `updateTime` | string | RFC 3339 timestamp |
| `property` | object | Has link/tasklist/code/incomplete tasks flags |
| `location` | object | Optional geo-location |

## Filter Syntax

Filters follow Google AIP-160 (CEL). Examples:
```
filter="row_status == \"NORMAL\""
filter="creator == \"users/1\""
```

## Tagging Notes

The MCP `memos_update` tool does not expose a `tags` parameter. To tag a note, append the tag to the end of the note content:

```
#tag1 #tag2
```

Then call `memos_update` with `updateMask="content"` and the updated content.
