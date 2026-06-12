---
name: firecrawl-cli
description: Use for web scraping, crawling, search, and data extraction from websites using the Firecrawl CLI tool. Commands: firecrawl scrape, firecrawl crawl, firecrawl search, firecrawl map, firecrawl agent, firecrawl parse.
---

# Firecrawl CLI

## Overview

Firecrawl CLI (`firecrawl`) provides web scraping, crawling, search, and AI-powered data extraction from the command line. Supports single-page scrape, full-site crawl, sitemap discovery, web search, local file parsing, and AI agent extraction.

## When to Use

- Scraping a URL to extract markdown, HTML, links, images, or screenshots
- Crawling an entire website with depth/limit controls
- Searching the web with optional result scraping
- Mapping/discovering URLs on a website via sitemap
- Parsing local files (PDF, DOCX, HTML, XLSX, etc.) into markdown/JSON
- Running an AI agent to extract structured data from web pages
- Asking questions about scraped/parsed content via `--query`

## Authentication

Before use, ensure the Firecrawl API key is configured:
```bash
# Check auth status
firecrawl view-config
# Login if not authenticated
firecrawl login
# Or set env var:
export FIRECRAWL_API_KEY="fc-..."
```

## Commands

### `firecrawl scrape` — Scrape URL(s)

Scrape one or more URLs concurrently. Multiple URLs are saved to `.firecrawl/`.

```bash
# Scrape a URL to markdown (default)
firecrawl scrape https://example.com

# Scrape with specific format
firecrawl scrape https://example.com -f markdown,links,images

# Scrape as HTML
firecrawl scrape https://example.com -H

# Scrape with screenshot
firecrawl scrape https://example.com --screenshot

# Scrape multiple URLs (concurrent, saved to .firecrawl/)
firecrawl scrape https://example.com https://example2.com

# Scrape with structured extraction (JSON schema)
firecrawl scrape https://example.com --schema '{"type":"object","properties":{"title":{"type":"string"}}}'

# Ask a question about the page
firecrawl scrape https://example.com -Q "What is the main topic?"

# Geo-targeted scrape
firecrawl scrape https://example.com --country DE --languages de

# Save output to file
firecrawl scrape https://example.com -o output.md

# Output as pretty JSON
firecrawl scrape https://example.com -f markdown,links --json --pretty

# Use persistent browser profile
firecrawl scrape https://example.com --profile my-session
```

### `firecrawl crawl` — Crawl a website

```bash
# Start a crawl
firecrawl crawl https://example.com

# Crawl with options
firecrawl crawl https://example.com --limit 50 --max-depth 3

# Include specific paths only
firecrawl crawl https://example.com --include-paths /blog/*,/docs/*

# Exclude paths
firecrawl crawl https://example.com --exclude-paths /*.pdf,/admin/*

# Wait for completion
firecrawl crawl https://example.com --wait --progress

# Check crawl job status
firecrawl crawl JOB_ID --status

# Cancel a running crawl
firecrawl crawl JOB_ID --cancel

# Advanced: pass scrape options to each page
firecrawl crawl https://example.com --scrape-options '{"formats":["markdown","links"],"onlyMainContent":true}'
```

### `firecrawl search` — Web search

```bash
# Basic search (5 results)
firecrawl search "latest AI news"

# More results
firecrawl search "latest AI news" --limit 20

# Search with scraping
firecrawl search "React 19 features" --scrape

# Search by source type
firecrawl search "climate change" --sources news

# Time-based search
firecrawl search "CES 2026" --tbs qdr:w  # past week
firecrawl search "CES 2026" --tbs qdr:m  # past month

# Filter by category
firecrawl search "firecrawl" --categories github

# Search with geotargeting
firecrawl search "restaurants" --location "Berlin,Germany"
```

### `firecrawl map` — Discover URLs on a site

```bash
# Map all URLs from sitemap
firecrawl map https://example.com

# Map with search filter
firecrawl map https://example.com --search blog

# Limit results
firecrawl map https://example.com --limit 100

# Include subdomains
firecrawl map https://example.com --include-subdomains

# Use sitemap only
firecrawl map https://example.com --sitemap only
```

### `firecrawl parse` — Parse local files

```bash
# Parse PDF to markdown
firecrawl parse document.pdf

# Parse with multiple formats
firecrawl parse document.pdf -f markdown,links

# Parse HTML file
firecrawl parse page.html -H

# Parse without boilerplate
firecrawl parse article.html --only-main-content

# Ask question about parsed content
firecrawl parse report.pdf -Q "What is the total revenue?"

# Parse to pretty JSON
firecrawl parse contract.docx --json --pretty -o output.json
```

Supported: `.html`, `.htm`, `.pdf`, `.docx`, `.doc`, `.odt`, `.rtf`, `.xlsx`, `.xls`
Max size: 50 MB

### `firecrawl agent` — AI data extraction

Use a natural language prompt to extract data from one or more URLs.

```bash
# Extract data with a prompt
firecrawl agent "Find all pricing plans on this page" --urls https://example.com/pricing

# Extract using specific model
firecrawl agent "List all team members" --urls https://example.com/about --model spark-1-pro

# Extract structured data via JSON schema
firecrawl agent "Extract product info" --urls https://example.com/products \
  --schema '{"type":"object","properties":{"name":{"type":"string"},"price":{"type":"number"}}}'

# Check agent status
firecrawl agent JOB_ID --status

# Cancel agent
firecrawl agent JOB_ID --cancel

# Wait for completion
firecrawl agent "Extract blog post titles" --urls https://example.com/blog --wait --progress
```

### `firecrawl config` / `firecrawl env` — Configuration

```bash
# View current config and auth status
firecrawl view-config

# Login / configure
firecrawl login

# Logout
firecrawl logout

# View version, auth status, concurrency, credits
firecrawl --status

# Pull API key into .env
firecrawl env

# Run diagnostics
firecrawl doctor
```

## Tips

- **Default output is markdown** for scrape and parse — use `-f` to customize
- **Save outputs to `.firecrawl/`** via multiple-URL scrape or `-o` for single
- **Use `--scrape` with search** to get both search results and page content
- **Use `--wait --progress`** for crawl/agent to get results in one call
- **Geo-targeting** works on scrape (`--country`, `--languages`)
- **Persistent profiles** (`--profile`) maintain session state across scrapes
- **Schema-based extraction** (`--schema`) structures data into JSON; use `--json --pretty` for readability
- **Use `--query`/`-Q`** to ask questions about content without reading the full page
- **Check credits** with `firecrawl --status`
