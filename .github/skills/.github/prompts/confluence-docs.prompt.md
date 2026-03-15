---
name: fetchConfluence
description: Quick command to collect Confluence pages as Markdown context files
agent: "Confluence Docs Collector"
argument-hint: "Enter Confluence URLs (one per line or comma-separated)"
---

# Collect Confluence Pages

Collect the provided Confluence pages and save them as Markdown files in `docs/confluence/`.

## Instructions

1. Parse all Confluence URLs from the input
2. For each URL:
   - Extract page ID or search by title
   - Fetch content using Atlassian MCP
   - Convert to clean Markdown
   - Save with descriptive filename
3. Report results

## Input

${input:urls:Paste Confluence URLs here}

## Output Location

All files will be saved to: `docs/confluence/`

Begin collecting the pages now.
