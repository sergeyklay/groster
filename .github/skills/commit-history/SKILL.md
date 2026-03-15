---
name: commit-history
description: Fetch commit history between package versions from GitHub when changelog is unavailable. Use this skill when (1) changelog analysis failed to provide sufficient information, (2) changelog exists but breaking changes are unclear, (3) evaluating packages without public release notes. Works with both npm/yarn (Node.js) and Composer (PHP) packages. Requires the package repository to be publicly accessible on GitHub.
---

# Commit history

Fallback analysis when standard changelog sources fail. Only supports public GitHub repositories.

## References

- [Commands reference](references/REFERENCE.md) - Detailed gh CLI commands for repository resolution, tag lookup, and commit extraction
- [Output templates](references/templates.md) - Report formats for complete, partial, and unavailable analysis results

## Workflow

1. **Detect ecosystem** - Node.js (npm/yarn) or PHP (Composer)
2. **Resolve repository URL** - Get GitHub repo from package metadata
3. **Extract owner/repo** - Parse URL to `owner/repo` format
4. **Resolve version tags** - Map package versions to Git tags
5. **Fetch commit comparison** - Use GitHub compare API
6. **Categorize commits** - Group by conventional commit type
7. **Generate report** - Structured analysis with recommendations

## Ecosystem detection

| Indicator | Ecosystem |
| --- | --- |
| `package.json` exists | Node.js (npm/yarn) |
| `composer.json` exists | PHP (Composer) |
| Package name starts with `@` | Node.js scoped package |
| Package name contains `/` (e.g., `vendor/package`) | PHP Composer package |

## Step 1: Resolve repository URL

Find the package's GitHub repository based on ecosystem.

**Node.js (npm/yarn):**

```bash
npm view <package-name> repository.url 2>/dev/null
```

**PHP (Composer):**

```bash
composer show <vendor/package> --format=json 2>/dev/null | jq -r '.source.url // empty'
```

Internal packages may point to GitLab/Bitbucket. This skill only supports **public GitHub repositories**.

## Step 2: Extract owner/repo

Parse the repository URL to extract GitHub owner and repo:

| URL format | Example | Extracted |
| --- | --- | --- |
| `git+https://github.com/owner/repo.git` | `git+https://github.com/axios/axios.git` | `axios/axios` |
| `https://github.com/owner/repo` | `https://github.com/facebook/react` | `facebook/react` |
| `git://github.com/owner/repo.git` | `git://github.com/lodash/lodash.git` | `lodash/lodash` |
| `git@github.com:owner/repo.git` | `git@github.com:symfony/console.git` | `symfony/console` |

Non-GitHub URLs indicate this skill cannot help. Return `COMMITS_UNAVAILABLE`.

## Step 3: Resolve version tags

Package versions must map to Git tags. Try patterns in order: `v1.2.3`, `1.2.3`, `release-1.2.3`.

```bash
gh api repos/<owner>/<repo>/tags --jq '.[0:20] | .[].name'
```

Match the version to the appropriate tag format for both source and target versions.

## Step 4: Fetch commit comparison

```bash
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag>
```

Returns `total_commits`, `commits[]` array, and `status` (ahead/behind/identical/diverged).

## Step 5: Categorize commits

| Prefix                            | Category     | Risk   |
| --------------------------------- | ------------ | ------ |
| `feat!:`, `BREAKING CHANGE`       | Breaking     | High   |
| `fix!:`                           | Breaking fix | High   |
| `feat:`, `feat(`                  | Feature      | Medium |
| `fix:`, `fix(`                    | Bug fix      | Low    |
| `perf:`                           | Performance  | Medium |
| `refactor:`                       | Refactor     | Medium |
| `chore:`, `docs:`, `ci:`, `test:` | Maintenance  | Low    |

Commits without conventional prefixes require manual review.

## Step 6: Generate analysis

Produce a structured report:
- Total commits between versions
- Categorized commit breakdown
- Potential breaking changes (based on `!` marker or message content)
- Notable features and fixes

See [output templates](references/templates.md) for report formats.

## Limitations

| Limitation                   | Impact                                        | Mitigation                                  |
| ---------------------------- | --------------------------------------------- | ------------------------------------------- |
| **GitHub only**              | GitLab, Bitbucket, internal repos unsupported | Report as unsupported                       |
| **Public repos only**        | Private GitHub repos require authentication   | Check if repo is accessible                 |
| **Tag format varies**        | Some packages don't tag releases              | Try common patterns, fallback if none match |
| **Non-conventional commits** | Cannot auto-categorize impact                 | Flag for manual review                      |
| **Monorepos**                | Commits may include unrelated changes         | Filter by package path if detectable        |

## Graceful degradation

**This skill must never block the dependency update workflow.**

When commit history cannot be retrieved:
1. Return `COMMITS_UNAVAILABLE` status with reason
2. Include what was attempted (repo resolution, accessibility, tags)
3. Recommend verification-based approach (typecheck, lint, build, test)

## Language

Communicate with the user in their language. However, ALL reports, summaries, and documentation written to project files MUST be in **English only**.
