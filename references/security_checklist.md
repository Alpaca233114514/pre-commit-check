# Security Checklist for Pre-Commit

Comprehensive security checks performed before each commit.

## Check Categories

### 1. Hardcoded Secrets Detection

Detects exposed credentials and sensitive tokens in source code.

**Checked items:**
- [ ] AWS Access Key ID (`AKIA...`)
- [ ] AWS Secret Access Key
- [ ] Generic API keys
- [ ] Generic secrets/tokens
- [ ] Hardcoded passwords
- [ ] Private key files (RSA, DSA, EC, OpenSSH)
- [ ] GitHub personal access tokens
- [ ] Slack tokens
- [ ] Bearer tokens
- [ ] Database connection strings with embedded credentials
- [ ] JWT tokens
- [ ] Hardcoded IP addresses (informational)

**Rules:**
- Documentation/comments are skipped (except private keys)
- Placeholder values (`YOUR_API_KEY`, `example`, `test-key`) are excluded
- False positive detection for common variable names

### 2. Vulnerability Pattern Scanning

Language-specific vulnerability detection.

**Universal checks:**
- [ ] `eval()` usage - Remote Code Execution risk
- [ ] `exec()` usage - Remote Code Execution risk
- [ ] Disabled SSL verification - Man-in-the-middle risk

**Python-specific:**
- [ ] SQL injection via string formatting (`cursor.execute("SELECT * FROM t WHERE id = %s" % value)`)
- [ ] Unsafe `pickle.loads()` - Deserialization RCE
- [ ] `subprocess` with `shell=True` - Command injection
- [ ] `DEBUG = True` in production code - Information disclosure

**JavaScript/TypeScript-specific:**
- [ ] `innerHTML` assignment - Cross-site scripting (XSS)
- [ ] `dangerouslySetInnerHTML` - React XSS
- [ ] `document.write()` - DOM-based XSS

### 3. Dependency Vulnerability Scanning

Checks third-party dependencies for known CVEs.

**Python:**
- Tool: `pip audit`
- Scans: `requirements.txt`, `pyproject.toml`
- Action: Update vulnerable packages

**Node.js:**
- Tool: `npm audit`
- Scans: `package.json` + `package-lock.json`
- Action: Run `npm audit fix`

### 4. File Permission Checks (Unix)

- [ ] World-writable files (`chmod o+w`) - Local privilege escalation risk

## Severity Classification

| Level | Color | Action Required |
|-------|-------|-----------------|
| Critical | Red | **BLOCK** commit immediately |
| High | Red | **BLOCK** commit immediately |
| Medium | Yellow | Warn, require review |
| Low | Green | Advisory, note in report |
| Info | Gray | Informational only |

## Pass Criteria

- **Security check passes** when: 0 Critical + 0 High severity findings
- **Security check fails** when: >=1 Critical or High severity finding

## Recommended Remediation

### For exposed secrets
1. Rotate the exposed credential immediately
2. Remove from code history (rewrite git history if committed)
3. Move to environment variables or secret management system
4. Add the file pattern to `.gitignore`

### For vulnerabilities
1. Replace dangerous functions with safe alternatives
2. Use parameterized queries for SQL
3. Use safe serialization (JSON instead of pickle)
4. Validate and sanitize all user inputs

### For dependency vulnerabilities
1. Update to patched versions
2. Run `pip audit` or `npm audit` regularly
3. Enable Dependabot or similar automated scanning
