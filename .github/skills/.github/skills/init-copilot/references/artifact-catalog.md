# Artifact catalog

All artifacts available for VS Code + GitHub Copilot projects. Source paths point to files in the Dev Copilot repository (`pdffiller/dev-copilot`, branch `main`). Most target paths are identical to source paths, except skills from `core/skills/` which install to `.github/skills/` in the target project. Use `source -> target` mapping syntax in the manifest for these.

## Table of contents

- [Meta-agents (generators)](#meta-agents-generators)
- [Specialized agents](#specialized-agents)
- [Prompt files](#prompt-files)
- [Instructions](#instructions)
- [Skills](#skills)
- [Configuration templates](#configuration-templates)

---

## Meta-agents (generators)

Temporary setup tools. The developer runs each generator once to produce a project-specific pipeline agent, then removes the generator file.

| Artifact            | Source path prefix            | Purpose                                                        |
| ------------------- | ----------------------------- | -------------------------------------------------------------- |
| AGENTS.md generator | `core/skills/context-files/`  | Generates AGENTS.md through codebase archaeology and interview |
| Architect generator | `core/skills/init-architect/` | Generates a project-specific Architect agent                   |
| Planner generator   | `core/skills/init-planner/`   | Generates a project-specific Planner agent                     |
| Coder generator     | `core/skills/init-coder/`     | Generates a project-specific Coder agent                       |
| Tester generator    | `core/skills/init-tester/`    | Generates a project-specific Tester agent                      |

Install to `.github/skills/` in the target project. Every file listed must be fetched.

**init-architect**

```
SKILL.md
assets/architect.copilot.md
```

**init-planner**

```
SKILL.md
assets/planner.copilot.md
```

**init-coder**

```
SKILL.md
assets/coder.copilot.md
```

**init-tester**

```
SKILL.md
assets/tester.copilot.md
```

---

## Specialized agents

Permanent agents for specific workflows. Install only what matches the project's stack.

| Artifact                  | Source path                               | Stack filter                 |
| ------------------------- | ----------------------------------------- | ---------------------------- |
| Confluence Docs Collector | `.github/agents/confluence-docs.agent.md` | All (requires Atlassian MCP) |
| Node.js Release Engineer  | `.github/agents/nodejs-re.agent.md`       | Node.js                      |
| PHP Release Engineer      | `.github/agents/php-re.agent.md`          | PHP                          |
| Writer                    | `.github/agents/writer.agent.md`          | All                          |

---

## Prompt files

Shortcuts for launching pipeline agents. Each prompt maps to one agent.

| Command            | Source path                                 | Agent                     |
| ------------------ | ------------------------------------------- | ------------------------- |
| `/specify`         | `.github/prompts/specify.prompt.md`         | Architect                 |
| `/plan`            | `.github/prompts/plan.prompt.md`            | Planner                   |
| `/implement`       | `.github/prompts/implement.prompt.md`       | Coder                     |
| `/test`            | `.github/prompts/test.prompt.md`            | Tester                    |
| `/createPr`        | `.github/prompts/pr.prompt.md`              | Default agent             |
| `/doc`             | `.github/prompts/doc.prompt.md`             | Writer                    |
| `/fetchConfluence` | `.github/prompts/confluence-docs.prompt.md` | Confluence Docs Collector |
| `/init-agents-md`  | `.github/prompts/init-agents-md.prompt.md`  | Default agent             |
| `/jira-task`       | `.github/prompts/jira-task.prompt.md`       | Default agent             |

---

## Instructions

Tactical rules attached automatically by `applyTo` file pattern or `description` relevance.

| Instruction     | Source path                                            | Stack filter | applyTo                                |
| --------------- | ------------------------------------------------------ | ------------ | -------------------------------------- |
| Writing style   | `.github/instructions/writing.instructions.md`         | All          | `docs/**/*.md`                         |
| Code review     | `.github/instructions/code-review.instructions.md`     | All          | By description                         |
| Commit messages | `.github/instructions/commit-messages.instructions.md` | All          | By description                         |
| Use npm         | `.github/instructions/use-npm.instructions.md`         | Node.js      | `**/package.json,**/package-lock.json` |
| PHP SignNow     | `.github/instructions/php-signnow.instructions.md`     | PHP          | `**/*.php`                             |
| pytest testing  | `.github/instructions/pytest-testing.instructions.md`  | Python       | `tests/**/*.py`                        |
| Confluence docs | `.github/instructions/confluence-docs.instruction.md`  | All          | `docs/confluence/**/*.md`              |

---

## Skills

Self-contained procedure packages following the agentskills.io specification. Copy the entire directory (SKILL.md + all subdirectories). Every file listed below must be fetched.

### Universal skills (all stacks)

**git-commit**

```
core/skills/git-commit/SKILL.md
core/skills/git-commit/references/commit-format.md
```

**creating-pr**

```
core/skills/creating-pr/SKILL.md
core/skills/creating-pr/assets/pull_request_template.md
```

**structuring-tasks**

```
core/skills/structuring-tasks/SKILL.md
core/skills/structuring-tasks/assets/task-template.md
```

**prompt-optimizer**

```
core/skills/prompt-optimizer/SKILL.md
```

**confluence-docs**

```
core/skills/confluence-docs/SKILL.md
core/skills/confluence-docs/references/conversion.md
```

**context-files**

```
core/skills/context-files/SKILL.md
core/skills/context-files/scripts/validate_context_file.py
core/skills/context-files/references/archaeological-checklist.md
core/skills/context-files/references/platform-formats.md
core/skills/context-files/assets/context-file-template.md
```

**creating-agent-skills**

```
core/skills/creating-agent-skills/SKILL.md
core/skills/creating-agent-skills/scripts/init_skill.py
core/skills/creating-agent-skills/scripts/validate_skill.py
core/skills/creating-agent-skills/references/frontmatter-fields.md
core/skills/creating-agent-skills/references/skills-ecosystem.md
core/skills/creating-agent-skills/references/writing-patterns.md
```

**commit-history**

```
core/skills/commit-history/SKILL.md
core/skills/commit-history/references/REFERENCE.md
core/skills/commit-history/references/templates.md
```

**comparing-solutions**

```
core/skills/comparing-solutions/SKILL.md
core/skills/comparing-solutions/references/document-structure.md
core/skills/comparing-solutions/references/evaluation-methodology.md
core/skills/comparing-solutions/references/writing-guidelines.md
core/skills/comparing-solutions/assets/comparison-template.md
```

**jira-syntax**

```
core/skills/jira-syntax/SKILL.md
core/skills/jira-syntax/assets/bug-report.md
core/skills/jira-syntax/assets/feature-request.md
core/skills/jira-syntax/references/syntax-reference.md
core/skills/jira-syntax/scripts/validate-jira-syntax.sh
```

### Node.js skills

**node-environment**

```
core/skills/node-environment/SKILL.md
```

**nodejs-changelog-analyzer**

```
core/skills/nodejs-changelog-analyzer/SKILL.md
core/skills/nodejs-changelog-analyzer/references/REFERENCE.md
core/skills/nodejs-changelog-analyzer/references/templates.md
```

### PHP skills

**php-environment**

```
core/skills/php-environment/SKILL.md
```

**php-changelog-analyzer**

```
core/skills/php-changelog-analyzer/SKILL.md
core/skills/php-changelog-analyzer/references/REFERENCE.md
core/skills/php-changelog-analyzer/references/templates.md
```

---

## Configuration templates

### MCP servers (`.vscode/mcp.json`)

```json
{
  "servers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "type": "http"
    }
  },
  "inputs": []
}
```

Add the Atlassian MCP server if the team uses Confluence:

```json
{
  "servers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "type": "http"
    },
    "com.atlassian/atlassian-mcp-server": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp"
    }
  },
  "inputs": []
}
```

### Copilot instructions (`.github/copilot-instructions.md`)

```markdown
Refer to [AGENTS.md](../AGENTS.md) for all repo instructions.
```
