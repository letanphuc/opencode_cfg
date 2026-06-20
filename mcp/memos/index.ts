import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { loadEnvFile } from "node:process";

const envFile = process.argv[2];
if (envFile) loadEnvFile(envFile);

const MEMOS_URL = process.env.MEMOS_URL?.replace(/\/+$/, "") || "http://localhost:5230";
const MEMOS_TOKEN = process.env.MEMOS_TOKEN || "";

const API = `${MEMOS_URL}/api/v1`;

async function api(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (MEMOS_TOKEN) headers["Authorization"] = `Bearer ${MEMOS_TOKEN}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Memos API error ${res.status}: ${body}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

const server = new Server(
  { name: "memos", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "memos_profile",
      description: "Get the Memos instance profile (version, demo mode, admin info, commit SHA)",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    {
      name: "memos_list",
      description: "List memos with optional filters, ordering, and pagination",
      inputSchema: {
        type: "object",
        properties: {
          pageSize: { type: "integer", description: "Max results (default 50, max 1000)" },
          pageToken: { type: "string", description: "Pagination token from previous response" },
          state: { type: "string", enum: ["STATE_UNSPECIFIED", "NORMAL", "ARCHIVED"], description: "Filter by memo state (default NORMAL)" },
          orderBy: { type: "string", description: "Sort order, e.g. 'pinned desc, create_time desc' or 'update_time asc'" },
          filter: { type: "string", description: "CEL filter expression, e.g. 'row_status == \"NORMAL\"'" },
          showDeleted: { type: "boolean", description: "Include deleted memos" },
        },
        required: [],
      },
    },
    {
      name: "memos_get",
      description: "Get a single memo by ID",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID (e.g. '1' or 'abc-123')" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_create",
      description: "Create a new memo",
      inputSchema: {
        type: "object",
        properties: {
          content: { type: "string", description: "The memo content in Markdown format" },
          visibility: { type: "string", enum: ["PRIVATE", "PROTECTED", "PUBLIC"], description: "Visibility level (default PRIVATE)" },
          state: { type: "string", enum: ["NORMAL", "ARCHIVED"], description: "Memo state (default NORMAL)" },
          memoId: { type: "string", description: "Optional custom ID. If empty, a unique ID will be generated" },
        },
        required: ["content"],
      },
    },
    {
      name: "memos_update",
      description: "Update a memo. You MUST specify updateMask with the fields you want to change.",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          updateMask: { type: "string", description: "Comma-separated field names to update, e.g. 'content,visibility,state,pinned'. Required." },
          content: { type: "string", description: "New Markdown content" },
          visibility: { type: "string", enum: ["PRIVATE", "PROTECTED", "PUBLIC"], description: "New visibility" },
          state: { type: "string", enum: ["NORMAL", "ARCHIVED"], description: "New state" },
          pinned: { type: "boolean", description: "Whether the memo is pinned" },
        },
        required: ["memo", "updateMask"],
      },
    },
    {
      name: "memos_delete",
      description: "Delete a memo permanently",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          force: { type: "boolean", description: "Delete even if the memo has associated data" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_comments_list",
      description: "List comments for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          pageSize: { type: "integer", description: "Max results" },
          pageToken: { type: "string", description: "Pagination token" },
          orderBy: { type: "string", description: "Sort order" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_comment_create",
      description: "Create a comment on a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The parent memo ID" },
          content: { type: "string", description: "Comment content in Markdown" },
          visibility: { type: "string", enum: ["PRIVATE", "PROTECTED", "PUBLIC"], description: "Visibility (default PRIVATE)" },
        },
        required: ["memo", "content"],
      },
    },
    {
      name: "memos_attachments_list",
      description: "List attachments for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_relations_list",
      description: "List relations for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_relations_set",
      description: "Set relations for a memo (replaces all existing relations)",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          relations: {
            type: "array",
            items: {
              type: "object",
              properties: {
                relatedMemo: { type: "string", description: "The related memo name, e.g. 'memos/2'" },
                type: { type: "string", enum: ["REFERENCE", "COMMENT"], description: "Relation type" },
              },
              required: ["relatedMemo", "type"],
            },
            description: "List of relations to set",
          },
        },
        required: ["memo", "relations"],
      },
    },
    {
      name: "memos_reactions_list",
      description: "List reactions for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_reaction_upsert",
      description: "Add or update a reaction on a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          reactionType: { type: "string", description: "Reaction type (e.g. 'emoji:heart', 'emoji:+1')" },
        },
        required: ["memo", "reactionType"],
      },
    },
    {
      name: "memos_reaction_delete",
      description: "Remove a reaction from a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
          reactionType: { type: "string", description: "Reaction type to remove" },
        },
        required: ["memo", "reactionType"],
      },
    },
    {
      name: "memos_shares_list",
      description: "List share links for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_share_create",
      description: "Create a share link for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_share_delete",
      description: "Delete a share link for a memo",
      inputSchema: {
        type: "object",
        properties: {
          memo: { type: "string", description: "The memo ID" },
        },
        required: ["memo"],
      },
    },
    {
      name: "memos_users_list",
      description: "List all users (admin only)",
      inputSchema: {
        type: "object",
        properties: {
          pageSize: { type: "integer", description: "Max results" },
          pageToken: { type: "string", description: "Pagination token" },
          filter: { type: "string", description: "Filter, e.g. 'username == \"steven\"'" },
          showDeleted: { type: "boolean", description: "Include deleted users" },
        },
        required: [],
      },
    },
    {
      name: "memos_user_get",
      description: "Get a user by username or ID",
      inputSchema: {
        type: "object",
        properties: {
          user: { type: "string", description: "The username or user ID (e.g. 'steven' or 'users/1')" },
        },
        required: ["user"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      // ── Instance ──
      case "memos_profile": {
        const data = await api("/instance/profile");
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      // ── Memos CRUD ──
      case "memos_list": {
        const params = new URLSearchParams();
        if (args?.pageSize) params.set("pageSize", String(args.pageSize));
        if (args?.pageToken) params.set("pageToken", String(args.pageToken));
        if (args?.state && args.state !== "STATE_UNSPECIFIED") params.set("state", String(args.state));
        if (args?.orderBy) params.set("orderBy", String(args.orderBy));
        if (args?.filter) params.set("filter", String(args.filter));
        if (args?.showDeleted) params.set("showDeleted", "true");
        const qs = params.toString();
        const data = await api(`/memos${qs ? `?${qs}` : ""}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_get": {
        const data = await api(`/memos/${args?.memo}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_create": {
        const body: Record<string, unknown> = { content: args?.content };
        if (args?.visibility) body.visibility = args.visibility;
        if (args?.state) body.state = args.state;
        const params = args?.memoId ? `?memoId=${args.memoId}` : "";
        const data = await api(`/memos${params}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_update": {
        const body: Record<string, unknown> = {};
        if (args?.content !== undefined) body.content = args.content;
        if (args?.visibility !== undefined) body.visibility = args.visibility;
        if (args?.state !== undefined) body.state = args.state;
        if (args?.pinned !== undefined) body.pinned = args.pinned;
        const data = await api(`/memos/${args?.memo}?updateMask=${args?.updateMask}`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_delete": {
        const params = args?.force ? "?force=true" : "";
        await api(`/memos/${args?.memo}${params}`, { method: "DELETE" });
        return { content: [{ type: "text", text: "Memo deleted successfully" }] };
      }

      // ── Comments ──
      case "memos_comments_list": {
        const params = new URLSearchParams();
        if (args?.pageSize) params.set("pageSize", String(args.pageSize));
        if (args?.pageToken) params.set("pageToken", String(args.pageToken));
        if (args?.orderBy) params.set("orderBy", String(args.orderBy));
        const qs = params.toString();
        const data = await api(`/memos/${args?.memo}/comments${qs ? `?${qs}` : ""}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_comment_create": {
        const body: Record<string, unknown> = { content: args?.content };
        if (args?.visibility) body.visibility = args.visibility;
        const data = await api(`/memos/${args?.memo}/comments`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      // ── Attachments ──
      case "memos_attachments_list": {
        const data = await api(`/memos/${args?.memo}/attachments`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      // ── Relations ──
      case "memos_relations_list": {
        const data = await api(`/memos/${args?.memo}/relations`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_relations_set": {
        const data = await api(`/memos/${args?.memo}/relations`, {
          method: "PATCH",
          body: JSON.stringify({ relations: args?.relations }),
        });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      // ── Reactions ──
      case "memos_reactions_list": {
        const data = await api(`/memos/${args?.memo}/reactions`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_reaction_upsert": {
        const data = await api(`/memos/${args?.memo}/reactions`, {
          method: "POST",
          body: JSON.stringify({ reactionType: args?.reactionType }),
        });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_reaction_delete": {
        await api(`/memos/${args?.memo}/reactions`, {
          method: "DELETE",
          body: JSON.stringify({ reactionType: args?.reactionType }),
        });
        return { content: [{ type: "text", text: "Reaction deleted" }] };
      }

      // ── Shares ──
      case "memos_shares_list": {
        const data = await api(`/memos/${args?.memo}/shares`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_share_create": {
        const data = await api(`/memos/${args?.memo}/shares`, { method: "POST" });
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_share_delete": {
        await api(`/memos/${args?.memo}/shares`, { method: "DELETE" });
        return { content: [{ type: "text", text: "Share link deleted" }] };
      }

      // ── Users ──
      case "memos_users_list": {
        const params = new URLSearchParams();
        if (args?.pageSize) params.set("pageSize", String(args.pageSize));
        if (args?.pageToken) params.set("pageToken", String(args.pageToken));
        if (args?.filter) params.set("filter", String(args.filter));
        if (args?.showDeleted) params.set("showDeleted", "true");
        const qs = params.toString();
        const data = await api(`/users${qs ? `?${qs}` : ""}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      case "memos_user_get": {
        const data = await api(`/users/${args?.user}`);
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      isError: true,
      content: [{ type: "text", text: `Error: ${message}` }],
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Memos MCP server failed:", err);
  process.exit(1);
});
