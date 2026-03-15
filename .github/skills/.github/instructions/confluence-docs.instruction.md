---
description: Collect Confluence pages as Markdown context files
applyTo: "docs/confluence/**/*.md"
---

# Confluence Context Documents

These documents were automatically collected from Confluence and serve as reference context for development tasks.

## How to Use This Context

When working with code that relates to these documents:

- Reference the YAML frontmatter for source information
- The `source_url` contains the original Confluence page link
- The `confluence_space` and `confluence_page_id` can be used for updates
- Check `collected_at` to understand how recent the information is

## Document Structure

Each document includes:

- YAML frontmatter with metadata
- Clean Markdown content from Confluence
- Code blocks preserved with original formatting
- Tables converted to Markdown syntax

## Keeping Context Fresh

If you need updated content:

- Use the `/fetchConfluence` prompt with the source URL
- Or ask the `@confluence-docs` (Confluence Docs Collector) agent to refresh specific pages

## Integration with Development

When implementing features based on these docs:

1. Reference the relevant context document
2. Follow the specifications as written
3. Note any discrepancies for documentation updates
