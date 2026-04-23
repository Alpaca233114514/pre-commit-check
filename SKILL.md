---
name: pre-commit-check
description: "发布前强制检查（Pre-commit release validation pipeline）: 在代码提交（git commit / git push）或发布/部署前强制运行，执行语言特定测试、安全漏洞扫描并生成结构化提交信息。当用户执行或提及 commit、push、publish、release、deploy，或提及发布前检查、pre-flight validation、commit readiness、代码质量门禁时必须触发。此检查为发布前的强制环节，不可跳过。"
rootUrl: https://raw.githubusercontent.com/Alpaca233114514/pre-commit-check/main/SKILL.md
---

# Pre-Commit Release Check

Three-phase validation pipeline that runs before code is committed:
1. **Code Testing** - Run language-specific tests, zero tolerance for failures
2. **Security Scan** - Detect secrets, vulnerabilities, and exposed credentials
3. **Commit Info Generation** - Produce formatted Conventional Commits message

## Workflow

```
1. Detect project type and languages → run detect_project.py
2. Run code tests → run run_tests.py
3. Run security scan → run security_scan.py
4. Generate commit info → run generate_commit_info.py
5. Present results → user decides to proceed
```

**All three phases must pass** before the commit is ready.

## Phase 1: Code Testing

Detect the project language and run the appropriate test tool automatically.

```bash
# Step 1: Detect project configuration
python3 scripts/detect_project.py [repo_path]

# Step 2: Run tests for all detected languages
python3 scripts/run_tests.py [repo_path]
```

**Pass criteria**: All test commands return exit code 0.

**Supported languages**: Python (pytest/unittest/tox), Node.js (jest/vitest/mocha), Go, Rust, Java (Maven/Gradle), Ruby (RSpec), PHP (PHPUnit), C# (dotnet).

**Strictness compliance**: Check for `CLAUDE.md`, `AGENT.md`, or equivalent project configuration files. If found, review and follow any testing standards or quality gates documented there. See `references/language_test_tools.md` for the complete tool matrix.

**On failure**: Report the failing test output, suggest fixes, and stop the pipeline.

## Phase 2: Security Scan

Scan the codebase for security issues before they reach the repository.

```bash
python3 scripts/security_scan.py [repo_path]
```

**Pass criteria**: 0 Critical + 0 High severity findings.

**Scan coverage**:
- Hardcoded secrets (API keys, tokens, passwords, private keys, database connection strings)
- Vulnerability patterns (SQL injection, XSS, RCE, unsafe deserialization)
- Dependency vulnerabilities (pip audit, npm audit)
- Insecure file permissions (world-writable files on Unix)

**On failure**: Print every Critical/High finding with file path, line number, and remediation guidance. Stop the pipeline until resolved. See `references/security_checklist.md` for the complete check matrix.

## Phase 3: Commit Info Generation

Generate a structured Conventional Commit message from the git diff.

```bash
# Staged changes (default)
python3 scripts/generate_commit_info.py [repo_path]

# Unstaged changes
python3 scripts/generate_commit_info.py [repo_path] --unstaged

# Override type or scope
python3 scripts/generate_commit_info.py [repo_path] --type-override fix --scope-override auth
```

**Output includes**:
- Auto-detected type (feat/fix/docs/style/refactor/test/chore/ci/perf)
- Auto-detected scope (from changed file paths)
- Breaking change detection
- Change statistics (files, insertions, deletions)
- Categorized file list

Review the generated message, apply overrides if needed, then use the final message for `git commit`.

## Reference Documents

- `references/language_test_tools.md` - Complete test tool matrix by language
- `references/security_checklist.md` - Full security check catalog and severity classification
- `references/commit_format.md` - Conventional Commits specification and examples

## Output Summary Format

Present results in this structure:

```
# Pre-Commit Check Results

## Phase 1: Code Tests
- Status: PASSED / FAILED
- Languages tested: [list]
- Details: [brief summary or failure output]

## Phase 2: Security Scan
- Status: PASSED / FAILED
- Findings: [X critical, Y high, Z medium, W low]
- Details: [list if any critical/high]

## Phase 3: Commit Message
```
[generated commit message]
```

## Recommendation
PROCEED / BLOCKED - [reason]
```

## Git Hooks Integration

Automatically enforce pre-commit-check on every `git commit` and `git push`.

### Install Hooks

```bash
python3 scripts/install_hooks.py [repo_path]
```

This creates two hooks in `.git/hooks/`:
- **`pre-commit`**: Runs code tests + security scan + generates commit message suggestion
- **`pre-push`**: Runs code tests + security scan (stricter gate before remote push)

**If any phase fails, the git operation is blocked** until issues are resolved.

### Hook Behavior

| Hook | Phase 1: Tests | Phase 2: Security | Phase 3: Commit Info |
|------|---------------|-------------------|---------------------|
| `pre-commit` | ✅ Block on fail | ✅ Block on fail | ℹ️ Info only |
| `pre-push` | ✅ Block on fail | ✅ Block on fail | ❌ Not run |

### Bypass Hooks (Emergency Only)

```bash
git commit --no-verify   # skip pre-commit hook
git push --no-verify     # skip pre-push hook
```

### Uninstall Hooks

Simply delete `.git/hooks/pre-commit` and `.git/hooks/pre-push`.

## Prerequisites

- Python 3.8+
- git installed and available in PATH
- Language-specific test tools installed (pytest, jest, go, cargo, etc.)
- For dependency scanning: `pip audit` (Python), `npm audit` (Node.js)
