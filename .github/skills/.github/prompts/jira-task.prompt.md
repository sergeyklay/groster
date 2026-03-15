---
name: jira-task
description: Create a Jira feature request or bug report from a file or free-form input
agent: agent
tools:
  - vscode/askQuestions
  - read/readFile
  - com.atlassian/atlassian-mcp-server/atlassianUserInfo
  - com.atlassian/atlassian-mcp-server/createJiraIssue
  - com.atlassian/atlassian-mcp-server/getAccessibleAtlassianResources
  - com.atlassian/atlassian-mcp-server/getJiraIssue
  - com.atlassian/atlassian-mcp-server/getJiraIssueTypeMetaWithFields
  - com.atlassian/atlassian-mcp-server/getJiraProjectIssueTypesMetadata
  - com.atlassian/atlassian-mcp-server/getVisibleJiraProjects
---

Create a Jira issue from the user's input. Return the issue key and a direct link when done.

## Skill

Read [jira-syntax](../skills/jira-syntax/SKILL.md) before writing any issue content. Every description and field value must use Jira wiki markup — never Markdown.

## Input

The user provides one of:

- **A file path** — read it with #tool:read/readFile and use the content as source material
- **Free-form text** — use it directly as source material

## Steps

1. **Parse input.** If the input looks like a file path (contains `/`, ends with `.md` or `.txt`), read the file. Otherwise treat it as raw text.
2. **Classify issue type.** Determine whether the source describes a bug (broken behavior, error, regression) or a feature request (new capability, improvement). When the intent is ambiguous, ask the user with #tool:vscode/askQuestions to clarify.
3. **Collect missing details.** Compare the source against required template fields from the jira-syntax skill. Ask the user for everything missing in a single batch — project key, priority, component, assignee, and any other required fields.
4. **Resolve Jira target.** Fetch the Atlassian cloud instance. Locate the project by key. Retrieve available issue types and required field metadata for the selected type.
5. **Compose the description.** Use the jira-syntax bug report template for bugs, the feature request template for features. Fill each section from the source material. Convert all formatting to Jira wiki markup.
6. **Validate.** Walk through the jira-syntax validation checklist. Fix any violations before proceeding.
7. **Create the issue.** Submit to Jira and return the issue key and URL to the user.
