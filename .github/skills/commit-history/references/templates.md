# Commit History Output Templates

## Full analysis report

Use when commits are successfully retrieved and categorized:

```markdown
## Commit History Analysis: <package-name>

**Version range:** <from-version> → <to-version>
**Ecosystem:** Node.js (npm) | PHP (Composer)
**Repository:** <owner>/<repo>
**Total commits:** <count>
**Status:** COMMITS_COMPLETE

### Commit breakdown

| Category  | Count   | Risk      |
| --------- | ------- | --------- |
| Breaking  | <count> | 🔴 High   |
| Features  | <count> | 🟡 Medium |
| Fixes     | <count> | 🟢 Low    |
| Refactors | <count> | 🟡 Medium |
| Other     | <count> | ⚪ Review |

### Breaking changes

| SHA     | Message   |
| ------- | --------- |
| `<sha>` | <message> |

_Review each breaking change before proceeding with update._

### Notable features

| SHA     | Message   |
| ------- | --------- |
| `<sha>` | <message> |

### Bug fixes

| SHA     | Message   |
| ------- | --------- |
| `<sha>` | <message> |

### Uncategorized commits

The following commits don't use conventional commit format:

| SHA     | Message   |
| ------- | --------- |
| `<sha>` | <message> |

_Manual review recommended for uncategorized commits._

### Recommendations

1. <Recommendation based on analysis>
2. <Recommendation based on analysis>
```

## Partial analysis report

Use when commits are retrieved but categorization is incomplete:

```markdown
## Commit History Analysis: <package-name>

**Version range:** <from-version> → <to-version>
**Repository:** <owner>/<repo>
**Total commits:** <count>
**Status:** COMMITS_PARTIAL

### Analysis limitations

<count> of <total> commits don't follow conventional commit format.
Automatic categorization is incomplete.

### Categorized commits

| Category      | Count   |
| ------------- | ------- |
| Breaking      | <count> |
| Features      | <count> |
| Fixes         | <count> |
| Uncategorized | <count> |

### Breaking changes detected

| SHA     | Message   |
| ------- | --------- |
| `<sha>` | <message> |

### All commits (uncategorized)

<list of all commit messages for manual review>

### Recommendations

1. **Manual review required** - Many commits lack conventional format
2. **Run full verification** - Rely on typecheck, lint, build, and test
3. **Test thoroughly** before deployment
```

## Unavailable report

Use when commit history cannot be retrieved:

```markdown
## Commit History Analysis: <package-name>

**Version range:** <from-version> → <to-version>
**Status:** COMMITS_UNAVAILABLE

### Analysis failed

**Reason:** <specific reason>

Possible causes:

- Repository not on GitHub (GitLab, Bitbucket, internal)
- Repository URL not specified in package.json
- Package version tags don't exist in repository
- Repository is private or inaccessible

### What was attempted

1. Repository URL resolution: <result>
2. GitHub accessibility check: <result>
3. Tag resolution: <result>

### Recommendations

1. **Proceed with caution** - No commit-level visibility available
2. **Run full verification** - Rely on typecheck, lint, build, and test
3. **Check package documentation** - Visit <homepage-url> for migration guides
4. **Review manually** - Clone repo and use `git log` for detailed analysis
```

## Large comparison warning

Append when commit count exceeds 250:

````markdown
### ⚠️ Comparison truncated

This comparison includes **<total>** commits, but GitHub's API returns a maximum of 250.

The analysis above covers the most recent 250 commits. For complete history:

```bash
git clone <repo-url> --depth=1
cd <repo>
git fetch --tags
git log <from-tag>..<to-tag> --oneline
```
````

## Integration with nodejs-changelog-analyzer

When used as fallback after nodejs-changelog-analyzer fails:

**Node.js packages:**

```markdown
## Package Analysis: <package-name>

**Version range:** <from-version> → <to-version>
**Ecosystem:** Node.js (npm)

### Changelog status

Standard changelog analysis failed:

- GitHub Releases: <reason>
- CHANGELOG.md: <reason>
- npm metadata: <reason>

### Fallback: Commit history analysis

<commit history analysis content>

### Combined recommendations

1. <recommendation>
2. <recommendation>
```

**PHP packages:**

```markdown
## Package Analysis: <vendor/package>

**Version range:** <from-version> → <to-version>
**Ecosystem:** PHP (Composer)

### Changelog status

Standard changelog analysis failed:

- GitHub Releases: <reason>
- CHANGELOG.md: <reason>
- Packagist metadata: <reason>

### Fallback: Commit history analysis

<commit history analysis content>

### Combined recommendations

1. <recommendation>
2. <recommendation>
```
