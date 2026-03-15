---
name: init-copilot
description: >
  Bootstrap VS Code + GitHub Copilot agent infrastructure in any project.
  Use when the user wants to initialize Dev Copilot, set up AI coding agents,
  install pipeline agents, instructions, skills, prompts, or MCP configuration,
  or says "initialize copilot", "bootstrap agents", "set up dev copilot",
  "configure agent infrastructure", "onboard project". Also use when asked
  to add specific Dev Copilot artifacts like AGENTS.md generator, meta-agents,
  or prompt files. Do NOT use for creating custom skills from scratch
  (use creating-agent-skills instead).
---

# Init Copilot

Bootstrap a complete VS Code + GitHub Copilot agent infrastructure in the developer's project. Detects the tech stack, presents relevant artifacts, installs them from the Dev Copilot repository, and configures the environment.

## Prerequisites

- VS Code with GitHub Copilot Chat extension (Agent Mode enabled)
- Network access to GitHub (or a local Dev Copilot clone as fallback)
- Bash shell available via terminal

## Workflow

### Phase 1: Scan environment

Run the detection script from the project root:

```bash
bash .github/skills/init-copilot/scripts/detect-stack.sh
```

The script outputs two sections:

- **STACKS** - Detected tech stacks (nodejs, php, python, go, java, rust, ruby, dotnet)
- **EXISTING** - Artifacts already present in the project

Parse both sections. Use detected stacks to filter artifact recommendations in Phase 2. Use existing artifacts to avoid overwriting files.

If no stacks are detected, ask the developer what tech stack they use.

### Phase 2: Select artifacts

Read `references/artifact-catalog.md` for the complete list of available artifacts with source paths and file listings.

Present artifact categories to the developer. Filter by detected stacks: hide Node.js-specific artifacts from PHP projects and vice versa. Mark artifacts that already exist (from the scan output) with a note.

**Categories to present:**

1. **AGENTS.md generation** - The `context-files` skill from `core/skills/`. Provides the full procedure for generating and validating context files. Recommend installing if AGENTS.md is missing.

2. **Pipeline agent generators** - Four generator skills from `core/skills/` (Architect, Planner, Coder, Tester). These are temporary: the developer runs each to generate a project-specific agent, then deletes the generator.

3. **Specialized agents** - Permanent agents for specific workflows (Writer, Confluence Docs Collector, Release Engineers). Filter by stack.

4. **Prompt files** - Slash commands (`/specify`, `/plan`, `/implement`, `/test`, `/createPr`, `/doc`). Recommend installing all core four: specify, plan, implement, test.

5. **Instructions** - Tactical coding rules (writing style, code review, commit messages, stack-specific standards). Filter by stack.

6. **Skills** - Procedure packages (git-commit, pull-request, PR naming/description, prompt-optimizer, changelog analyzers, environment managers). Filter by stack.

7. **MCP configuration** - Context7 server (recommended for all projects). Atlassian MCP server (if the team uses Confluence).

Offer a **"full install"** option that includes everything relevant to the detected stack. This is the recommended path for new projects.

Let the developer pick categories or individual items. Record their selections.

### Phase 3: Build the manifest

Based on the developer's selections, construct a manifest file listing every file path to fetch. Write the manifest to a temporary file (e.g., `/tmp/dc-manifest.txt`).

**Manifest write method (required):**

- Prefer editor/file tools that write exact file content (`create_file`/`apply_patch`) for long manifests.
- If a shell command is required, do not trust terminal output for correctness. Always run integrity checks immediately after writing.
- Avoid proceeding to install if the file fails validation.

**Rules for building the manifest:**

- For single-file artifacts (agents, prompts, instructions), add one line with the source path
- For skills with subdirectories, add one line per file (SKILL.md, each reference, each script, each asset). The full file lists are in `references/artifact-catalog.md`
- Skills from `core/skills/` install to `.github/skills/` in the target project. Use `source -> target` mapping syntax
- Do NOT include files the scan reported as already existing, unless the developer explicitly chose to overwrite
- Do NOT include the init-copilot skill itself (it's already in the project)

**Example manifest:**

```
# Meta-agent generators (core/skills/ -> .github/skills/)
core/skills/init-architect/SKILL.md -> .github/skills/init-architect/SKILL.md
core/skills/init-architect/assets/architect.claude.md -> .github/skills/init-architect/assets/architect.claude.md
core/skills/init-architect/assets/architect.copilot.md -> .github/skills/init-architect/assets/architect.copilot.md
core/skills/init-planner/SKILL.md -> .github/skills/init-planner/SKILL.md
core/skills/init-planner/assets/planner.claude.md -> .github/skills/init-planner/assets/planner.claude.md
core/skills/init-planner/assets/planner.copilot.md -> .github/skills/init-planner/assets/planner.copilot.md
core/skills/init-coder/SKILL.md -> .github/skills/init-coder/SKILL.md
core/skills/init-coder/assets/coder.claude.md -> .github/skills/init-coder/assets/coder.claude.md
core/skills/init-coder/assets/coder.copilot.md -> .github/skills/init-coder/assets/coder.copilot.md
core/skills/init-tester/SKILL.md -> .github/skills/init-tester/SKILL.md
core/skills/init-tester/assets/tester.claude.md -> .github/skills/init-tester/assets/tester.claude.md
core/skills/init-tester/assets/tester.copilot.md -> .github/skills/init-tester/assets/tester.copilot.md

# Prompts
.github/prompts/specify.prompt.md
.github/prompts/plan.prompt.md
.github/prompts/implement.prompt.md
.github/prompts/test.prompt.md
.github/prompts/pr.prompt.md
.github/prompts/doc.prompt.md
.github/prompts/confluence-docs.prompt.md
.github/prompts/init-agents-md.prompt.md
.github/prompts/jira-task.prompt.md

# Instructions
.github/instructions/writing.instructions.md
.github/instructions/code-review.instructions.md
.github/instructions/commit-messages.instructions.md

# Skills (core/skills/ -> .github/skills/)
core/skills/context-files/SKILL.md -> .github/skills/context-files/SKILL.md
core/skills/context-files/scripts/validate_context_file.py -> .github/skills/context-files/scripts/validate_context_file.py
core/skills/context-files/references/archaeological-checklist.md -> .github/skills/context-files/references/archaeological-checklist.md
core/skills/context-files/references/platform-formats.md -> .github/skills/context-files/references/platform-formats.md
core/skills/context-files/assets/context-file-template.md -> .github/skills/context-files/assets/context-file-template.md

core/skills/git-commit/SKILL.md -> .github/skills/git-commit/SKILL.md
core/skills/git-commit/references/commit-format.md -> .github/skills/git-commit/references/commit-format.md
core/skills/creating-pr/SKILL.md -> .github/skills/creating-pr/SKILL.md
core/skills/creating-pr/assets/pull_request_template.md -> .github/skills/creating-pr/assets/pull_request_template.md
core/skills/structuring-tasks/SKILL.md -> .github/skills/structuring-tasks/SKILL.md
core/skills/structuring-tasks/assets/task-template.md -> .github/skills/structuring-tasks/assets/task-template.md

core/skills/jira-syntax/SKILL.md -> .github/skills/jira-syntax/SKILL.md
core/skills/jira-syntax/assets/bug-report.md -> .github/skills/jira-syntax/assets/bug-report.md
core/skills/jira-syntax/assets/feature-request.md -> .github/skills/jira-syntax/assets/feature-request.md
core/skills/jira-syntax/references/syntax-reference.md -> .github/skills/jira-syntax/references/syntax-reference.md
core/skills/jira-syntax/scripts/validate-jira-syntax.sh -> .github/skills/jira-syntax/scripts/validate-jira-syntax.sh
```

### Phase 4: Install artifacts

Run the batch installer from the project root:

```bash
bash .github/skills/init-copilot/scripts/install-artifacts.sh /tmp/dc-manifest.txt
```

The script calls `fetch-artifact.sh` for each line in the manifest. It reports INSTALLED, SKIP, or FAIL per file and prints a summary.

- If the script reports failures, check the error messages
- For authentication issues with private repos, instruct: `gh auth login`
- For network failures, suggest a local clone fallback:

```bash
git clone https://github.com/pdffiller/dev-copilot.git ~/dev-copilot
export DEVCOPILOT_LOCAL=~/dev-copilot
```

Then re-run the install command.

### Phase 5: Configure MCP servers

If the developer selected MCP configuration:

1. Check if `.vscode/mcp.json` already exists
2. If it exists, read it and merge new servers into the existing `servers` object. Do not overwrite existing server entries.
3. If it does not exist, create `.vscode/mcp.json` using the template from `references/artifact-catalog.md` (see the "Configuration templates" section)
4. Ask the developer whether they use Confluence. Include the Atlassian MCP server only if they do.

### Phase 6: Create copilot-instructions.md

If `.github/copilot-instructions.md` does not exist:

```bash
mkdir -p .github
```

Create `.github/copilot-instructions.md` with content:

```markdown
Refer to [AGENTS.md](../AGENTS.md) for all repo instructions.
```

If the file already exists, skip this step.

### Phase 7: Verify

Run verification against the same manifest:

```bash
bash .github/skills/init-copilot/scripts/verify-setup.sh /tmp/dc-manifest.txt
```

Also verify non-manifest items:

- `.vscode/mcp.json` exists (if MCP was selected)
- `.github/copilot-instructions.md` exists

Report the verification results. If any files are missing, diagnose and fix before proceeding.

Clean up the temporary manifest:

```bash
rm -f /tmp/dc-manifest.txt
```

### Phase 8: Report and next steps

Summarize what was installed:

- Detected stacks
- Number of artifacts installed, skipped, and failed
- MCP configuration status
- Bridge file status

Then provide the next steps checklist. The order matters because each step depends on the previous one:

1. **Generate AGENTS.md** (if `context-files` skill was installed and AGENTS.md doesn't exist yet):
   - Select the "Init AGENTS.md" agent from the Copilot agent dropdown
   - Prompt: `Analyze this codebase and generate AGENTS.md. STRICTLY follow your instructions.`
   - Review the generated file before continuing

2. **Generate pipeline agents** (run each in a separate chat session, in order):
   - Select "Init Architect" → `Generate the Architect agent for this project. Follow your instructions strictly.`
   - Select "Init Planner" → `Generate the Planner agent for this project. Follow your instructions strictly.`
   - Select "Init Coder" → `Generate the Coder agent for this project. Follow your instructions strictly.`
   - Select "Init Tester" → `Generate the Tester agent for this project. Follow your instructions strictly.`
   - Review each generated agent

3. **Remove generator skills** after all agents are generated (optional):
   ```bash
   rm -rf .github/skills/init-architect .github/skills/init-planner .github/skills/init-coder .github/skills/init-tester
   ```

4. **Verify MCP servers** - Open Copilot Chat in Agent Mode, check the tools icon for MCP server availability

5. **Commit everything** to the repository

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `fetch-artifact.sh` returns non-zero | Network issue or wrong path | Check `DEVCOPILOT_REPO` and `DEVCOPILOT_BRANCH` env vars. Try local clone fallback. |
| 404 when fetching | File path changed upstream | Verify path against `references/artifact-catalog.md`. |
| Permission denied on script | Script not executable | Run `chmod +x .github/skills/init-copilot/scripts/*.sh` |
| Authentication error | Private repo, missing token | Run `gh auth login` then retry. |
| Existing file conflict | Artifact already installed | Scan output listed it; skip unless developer chose to overwrite. |

## Private repository support

For organizations using a private fork of Dev Copilot:

```bash
export DEVCOPILOT_REPO="your-org/dev-copilot-fork"
export DEVCOPILOT_BRANCH="main"
```

The `fetch-artifact.sh` script tries `gh api` (authenticated) before `curl` (public). For private repos without `gh`, clone locally:

```bash
git clone https://github.com/your-org/dev-copilot-fork.git ~/dev-copilot
export DEVCOPILOT_LOCAL=~/dev-copilot
```

## Language

All output, file content, commit messages, and status reports in English.
