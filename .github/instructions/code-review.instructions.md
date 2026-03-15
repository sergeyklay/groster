---
description: Use these instructions to guide your code reviews.
excludeAgent: ["coding-agent"]
---

# Code Review Guidelines

Guidelines for code reviews with Copilot.

**Important**: When reviewing code in specific languages or technologies, refer to the corresponding instruction files in `.github/instructions/` directory for language-specific best practices, conventions, and review criteria.

## Scope

1. **Correctness** — Does the code do what it claims?
2. **Safety** — Are there potential security vulnerabilities?
3. **Architecture** — Does the code fit well within the existing architecture and common conventions (see [AGENTS.md](../../AGENTS.md) for details)?

## Security Critical Issues

- Check for hardcoded secrets, API keys, or credentials
- Look for SQL injection and XSS vulnerabilities
- Verify proper input validation and sanitization
- Review authentication and authorization logic

## Performance Red Flags

- Identify N+1 database query problems
- Spot inefficient loops and algorithmic issues
- Check for memory leaks and resource cleanup
- Review caching opportunities for expensive operations

## Code Quality Essentials

- Functions should be focused and appropriately sized
- Use clear, descriptive naming conventions
- Ensure proper error handling throughout

## Review Style

- Be specific and actionable in feedback
- Explain the "why" behind recommendations
- Acknowledge good patterns when you see them
- Ask clarifying questions when code intent is unclear

## Documentation Hygiene

Flag when changes require documentation updates:

**AGENTS.md** — Update when:
- New architectural patterns or layer boundaries introduced
- Critical files added/removed/renamed
- Core philosophy or conventions change

**docs/** — Update when:
- User-facing features added or behavior changed
- Configuration options modified
- Setup/deployment steps affected

Do NOT require docs for: bug fixes, refactors with no API change, test additions, dependency updates and minor changes that do not affect usage.
