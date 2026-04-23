# Commit Message Format Specification

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

## Format

```
<type>(<scope>): <description>

[body]

[footer]
```

## Components

### Type (required)

| Type | Description | When to use |
|------|-------------|-------------|
| `feat` | New feature | Adding new functionality |
| `fix` | Bug fix | Fixing a bug |
| `docs` | Documentation | Changes to documentation only |
| `style` | Code style | Formatting, semicolons, etc. (no logic change) |
| `refactor` | Refactoring | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance | Performance improvement |
| `test` | Testing | Adding or updating tests |
| `chore` | Maintenance | Build process, dependencies, tooling |
| `ci` | CI/CD | Continuous Integration / Deployment changes |
| `build` | Build system | Build system or external dependency changes |
| `revert` | Revert | Reverting a previous commit |

### Scope (optional)

- Auto-detected from changed file paths
- Represents the area of codebase affected
- Examples: `auth`, `api`, `ui`, `db`, `config`, `deps`

### Description (required)

- Imperative mood ("add feature" not "added feature" or "adds feature")
- No capitalized first letter
- No trailing period
- Maximum 72 characters for the full subject line

### Body (optional)

- Explain **what** and **why**, not **how**
- Wrap at 72 characters
- Include change statistics and file list

### Footer (optional)

- Reference issues: `Fixes #123`, `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`

## Breaking Changes

Append `!` after type/scope for breaking changes:

```
feat(api)!: change authentication response format
```

## Examples

```
feat(auth): add OAuth2 login with Google
```

```
fix(api): handle null pointer in user validation

Add null check before accessing user.email field.
Prevent 500 error on /api/users endpoint.
```

```
feat(db)!: migrate from MongoDB to PostgreSQL

BREAKING CHANGE: Database schema completely redesigned.
All existing data must be migrated using scripts/migrate-v2.sh.
```

## Auto-Generated Information

The commit info script provides:
- **Type detection**: Based on file types and change patterns
- **Scope detection**: Most frequently changed directory/module
- **Statistics**: Files changed, insertions, deletions
- **Breaking change detection**: Signature changes, BREAKING markers
- **File summary**: List of all changed files with status (added/modified/deleted)

## Quality Criteria

A good commit message should:
- [x] Use correct type for the change
- [x] Include scope when applicable
- [x] Describe what changed in imperative mood
- [x] Include body for non-trivial changes
- [x] Reference related issues in footer
- [x] Mark breaking changes with `!`
