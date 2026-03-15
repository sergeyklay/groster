# Commit History Commands Reference

Detailed commands for fetching and analyzing commit history between package versions.

## Repository URL resolution

### From npm registry (Node.js)

```bash
# Get repository URL
npm view <package-name> repository.url 2>/dev/null

# Get repository object (includes type and url)
npm view <package-name> repository --json 2>/dev/null

# Get homepage as fallback
npm view <package-name> homepage 2>/dev/null

# Get bugs URL (often points to GitHub issues)
npm view <package-name> bugs.url 2>/dev/null
```

### From Composer registry (PHP)

```bash
# Get source URL from installed package
composer show <vendor/package> --format=json 2>/dev/null | jq -r '.source.url // empty'

# Get homepage
composer show <vendor/package> --format=json 2>/dev/null | jq -r '.homepage // empty'

# Get source info via Packagist API
curl -s "https://repo.packagist.org/p2/<vendor>/<package>.json" | jq -r '.packages["<vendor/package>"][0].source.url // empty'
```

### URL parsing patterns

Extract `owner/repo` from various URL formats:

```bash
# Pattern: git+https://github.com/owner/repo.git
echo "git+https://github.com/axios/axios.git" | sed -E 's|.*github\.com[:/]([^/]+/[^/.]+)(\.git)?|\1|'
# Output: axios/axios

# Pattern: https://github.com/owner/repo
echo "https://github.com/facebook/react" | sed -E 's|.*github\.com/([^/]+/[^/]+).*|\1|'
# Output: facebook/react

# Pattern: git://github.com/owner/repo.git
echo "git://github.com/lodash/lodash.git" | sed -E 's|.*github\.com[:/]([^/]+/[^/.]+)(\.git)?|\1|'
# Output: lodash/lodash

# Pattern: git@github.com:owner/repo.git (SSH format, common in PHP)
echo "git@github.com:symfony/console.git" | sed -E 's|.*github\.com[:/]([^/]+/[^/.]+)(\.git)?|\1|'
# Output: symfony/console
```

### Verify repository accessibility

```bash
# Check if repository exists and is accessible
gh api repos/<owner>/<repo> --jq '.full_name' 2>/dev/null
```

## Tag resolution

### List available tags

```bash
# List recent tags (first 20)
gh api repos/<owner>/<repo>/tags --jq '.[0:20] | .[].name'

# List all tags matching a pattern
gh api repos/<owner>/<repo>/tags --paginate --jq '.[].name' | grep -E '^v?<major>\.'

# Get tag for specific version
gh api repos/<owner>/<repo>/tags --paginate --jq '.[] | select(.name | test("^v?<version>$")) | .name'
```

### Common tag patterns

```bash
# Try v-prefixed first (most common)
gh api repos/<owner>/<repo>/git/refs/tags/v<version> --jq '.ref' 2>/dev/null

# Try plain version number
gh api repos/<owner>/<repo>/git/refs/tags/<version> --jq '.ref' 2>/dev/null

# Try release- prefix
gh api repos/<owner>/<repo>/git/refs/tags/release-<version> --jq '.ref' 2>/dev/null
```

### Monorepo package tags

Some monorepos prefix tags with package name:

```bash
# Pattern: package@version
gh api repos/<owner>/<repo>/tags --jq '.[] | select(.name | startswith("<package>@")) | .name'

# Example: @babel/core@7.23.0
gh api repos/babel/babel/tags --jq '.[] | select(.name | startswith("@babel/core@")) | .name' | head -5
```

## Commit comparison

### Fetch commits between tags

```bash
# Basic comparison
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag>

# Get comparison metadata only
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '{
  total_commits: .total_commits,
  ahead_by: .ahead_by,
  behind_by: .behind_by,
  status: .status
}'
```

### Extract commit details

```bash
# All commits with short SHA and first line of message
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  .commits[] | {
    sha: .sha[0:7],
    message: .commit.message | split("\n")[0],
    author: .commit.author.name,
    date: .commit.author.date
  }'

# Commits as simple list
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  .commits[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'
```

### Filter by conventional commit type

```bash
# Breaking changes only
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  [.commits[] | select(.commit.message | test("^[a-z]+!:|BREAKING CHANGE"; "i"))] |
  .[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'

# Features only
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  [.commits[] | select(.commit.message | test("^feat"; "i"))] |
  .[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'

# Fixes only
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  [.commits[] | select(.commit.message | test("^fix"; "i"))] |
  .[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'

# Features and fixes combined
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  [.commits[] | select(.commit.message | test("^(feat|fix)"; "i"))] |
  .[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'
```

### Categorize all commits

```bash
# Count commits by type
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  .commits | {
    total: length,
    breaking: [.[] | select(.commit.message | test("^[a-z]+!:|BREAKING CHANGE"; "i"))] | length,
    feat: [.[] | select(.commit.message | test("^feat[:(]"; "i"))] | length,
    fix: [.[] | select(.commit.message | test("^fix[:(]"; "i"))] | length,
    refactor: [.[] | select(.commit.message | test("^refactor[:(]"; "i"))] | length,
    chore: [.[] | select(.commit.message | test("^chore[:(]"; "i"))] | length,
    other: [.[] | select(.commit.message | test("^(feat|fix|refactor|chore|docs|test|ci|build|perf|style)[:(]"; "i") | not)] | length
  }'
```

### Handle pagination for large comparisons

```bash
# GitHub compare API returns max 250 commits
# For larger ranges, check total and warn user
gh api repos/<owner>/<repo>/compare/<from-tag>...<to-tag> --jq '
  if .total_commits > 250 then
    "Warning: \(.total_commits) commits, showing first 250"
  else
    "Total commits: \(.total_commits)"
  end'
```

## Version detection

### Node.js: Get package version

```bash
# From package.json in current project
cat package.json | jq -r '.dependencies["<package>"] // .devDependencies["<package>"]'

# From npm list
npm list <package> --depth=0 2>/dev/null | grep <package>

# Latest from registry
npm view <package-name> version

# Latest with dist-tag
npm view <package-name> dist-tags --json
```

### PHP: Get package version

```bash
# From composer.json in current project
cat composer.json | jq -r '.require["<vendor/package>"] // ."require-dev"["<vendor/package>"]'

# From composer show (installed version)
composer show <vendor/package> --format=json 2>/dev/null | jq -r '.versions[0]'

# Latest from Packagist
curl -s "https://repo.packagist.org/p2/<vendor>/<package>.json" | jq -r '.packages["<vendor/package>"][0].version'
```

## Error handling

| Error                | Cause                                  | Resolution                   |
| -------------------- | -------------------------------------- | ---------------------------- |
| `Not Found`          | Repository doesn't exist or is private | Return `COMMITS_UNAVAILABLE` |
| `Bad credentials`    | gh CLI not authenticated               | Run `gh auth login`          |
| `No tag found`       | Version tags don't exist               | Try alternative tag patterns |
| `No common ancestor` | Tags are unrelated                     | Return `COMMITS_UNAVAILABLE` |
| `Response too large` | Too many commits between versions      | Note truncation in report    |

## GitHub CLI authentication

```bash
# Check authentication status
gh auth status

# Authenticate if needed
gh auth login --web

# Verify repo access
gh repo view <owner>/<repo> --json name
```
