---
name: perplexity-search
description: Use ONLY when the user needs real-time web search, current information, deep research, or complex reasoning. Use the `pc` CLI to query Perplexity models via OpenRouter. Commands: pc search, pc ask, pc reason, pc research.
---

# Perplexity Search via CLI

You have access to the `pc` CLI tool to query Perplexity models through OpenRouter. Use it when you need up-to-date information from the web, deep research, or advanced reasoning beyond your training data.

## Available Commands

| Command | Default Model | Use Case |
|---------|---------------|----------|
| `pc search` | `perplexity/sonar` | Quick web search with ranked results |
| `pc ask` | `perplexity/sonar-pro` | General Q&A with real-time search |
| `pc reason` | `perplexity/sonar-reasoning-pro` | Complex analytical/coding tasks |
| `pc research` | `perplexity/sonar-deep-research` | Comprehensive deep-dive reports |

## When to Use

- **Current events**: anything after your knowledge cutoff — news, releases, CVEs, trends
- **Live documentation**: latest API docs, package versions, changelogs
- **Fact-checking**: verify claims, find sources, cross-reference information
- **Research**: in-depth analysis requiring multiple sources and citations
- **Complex reasoning**: multi-step problems where web context helps
- **Comparison**: comparing tools, libraries, services with current data

## How to Use

Run via `bash` with the `pc` command. Always use `--no-stream` to ensure clean output capture:

```
bash: pc ask --no-stream "What is the current best practice for React Server Components error handling?"
bash: pc search --no-stream "Next.js 15 new features 2025"
bash: pc reason --no-stream "Analyze the tradeoffs between Bun and Node.js for a production API server"
bash: pc research --no-stream "Comprehensive overview of WebAssembly GC adoption across browsers and runtimes"
```

## Tips

- **Prefer `pc ask --no-stream` for most cases** — it returns direct, well-formatted answers
- **Be specific** — narrow queries get better results than broad ones
- **Use `pc search --no-stream`** for raw ranked results when you need to inspect individual sources
- **Use `pc research --no-stream`** for deep dives requiring comprehensive analysis (may take several minutes)
- **Use `pc reason --no-stream`** when you need step-by-step analytical thinking with web context
- Results may include citations — reference them when presenting information to the user
- Use `--no-citations` to strip citation markers if they clutter the output
