#!/usr/bin/env python3
"""
Security scanner for pre-commit checks.
Detects:
- Hardcoded secrets (API keys, tokens, passwords)
- Common vulnerability patterns
- Dependency vulnerabilities
- Insecure file permissions
- Sensitive data exposure
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Patterns for detecting hardcoded secrets
SECRET_PATTERNS = [
    {
        "name": "AWS Access Key ID",
        "pattern": r"AKIA[0-9A-Z]{16}",
        "severity": "high",
        "description": "AWS Access Key ID detected",
    },
    {
        "name": "AWS Secret Access Key",
        "pattern": r"['\"\s][Ss][Ee][Cc][Rr][Ee][Tt][_\s-]?[Kk][Ee][Yy]['\"\s]\s*[:=]\s*['\"][a-zA-Z0-9/+=]{40}['\"]",
        "severity": "high",
        "description": "AWS Secret Access Key detected",
    },
    {
        "name": "Generic API Key",
        "pattern": r"['\"\s][Aa][Pp][Ii][_\s-]?[Kk][Ee][Yy]['\"\s]\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
        "severity": "high",
        "description": "Potential API key detected",
    },
    {
        "name": "Generic Secret",
        "pattern": r"['\"\s][Ss][Ee][Cc][Rr][Ee][Tt]['\"\s]\s*[:=]\s*['\"][a-zA-Z0-9_\-]{8,}['\"]",
        "severity": "medium",
        "description": "Potential secret detected",
    },
    {
        "name": "Password in Code",
        "pattern": r"['\"\s][Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]['\"\s]\s*[:=]\s*['\"][^'\"]{4,}['\"]",
        "severity": "high",
        "description": "Hardcoded password detected",
    },
    {
        "name": "Private Key",
        "pattern": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "severity": "critical",
        "description": "Private key file detected",
    },
    {
        "name": "GitHub Token",
        "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,}",
        "severity": "high",
        "description": "GitHub personal access token detected",
    },
    {
        "name": "Slack Token",
        "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}(-[a-zA-Z0-9]{24})?",
        "severity": "high",
        "description": "Slack token detected",
    },
    {
        "name": "Bearer Token",
        "pattern": r"[Bb]earer\s+[a-zA-Z0-9_\-\.]{20,}",
        "severity": "medium",
        "description": "Potential bearer token detected",
    },
    {
        "name": "Database Connection String",
        "pattern": r"(mongodb(\+srv)?|postgres(ql)?|mysql|redis|amqp)://[^:]+:[^@]+@",
        "severity": "high",
        "description": "Database connection string with credentials",
    },
    {
        "name": "JWT Token",
        "pattern": r"eyJ[A-Za-z0-9_\-]*\.eyJ[A-Za-z0-9_\-]*\.[A-Za-z0-9_\-]*",
        "severity": "medium",
        "description": "Potential JWT token detected",
    },
    {
        "name": "IP Address",
        "pattern": r"\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "severity": "info",
        "description": "Hardcoded IP address detected",
    },
]

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".scala",
    ".yml", ".yaml", ".json", ".xml", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".zsh", ".fish", ".ps1",
    ".md", ".txt", ".env", ".conf", ".config",
}

# Files/directories to exclude
EXCLUDE_PATHS = {
    ".git", ".svn", ".hg", "node_modules", "vendor", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".mypy_cache", "target", "build",
    "dist", ".next", ".nuxt", ".idea", ".vscode", "*.min.js", "*.min.css",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "CHANGELOG", "LICENSE", ".gitignore", ".gitattributes",
}


def should_scan_file(file_path: Path) -> bool:
    """Determine if a file should be scanned."""
    # Check excluded paths
    for part in file_path.parts:
        if any(excl in part for excl in EXCLUDE_PATHS):
            return False

    # Check extensions
    if file_path.suffix not in SCAN_EXTENSIONS:
        # Always scan .env files regardless of extension
        if file_path.name.startswith(".") and "env" in file_path.name:
            return True
        return False

    return True


def scan_file_for_secrets(file_path: Path) -> list[dict]:
    """Scan a single file for secret patterns."""
    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
    except (IOError, OSError):
        return findings

    for rule in SECRET_PATTERNS:
        pattern = rule["pattern"]
        for line_num, line in enumerate(lines, 1):
            # Skip comments for documentation files
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                # Still scan for private keys even in comments
                if "PRIVATE KEY" not in rule["name"]:
                    continue

            for match in re.finditer(pattern, line):
                # Filter out false positives
                matched_text = match.group(0)
                if is_false_positive(matched_text, rule["name"]):
                    continue

                findings.append({
                    "file": str(file_path),
                    "line": line_num,
                    "column": match.start() + 1,
                    "type": "secret",
                    "rule": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "match": matched_text[:50] + "..." if len(matched_text) > 50 else matched_text,
                })

    return findings


def is_false_positive(match: str, rule_name: str) -> bool:
    """Check if a match is a known false positive."""
    # Skip placeholder values
    placeholders = [
        "your-api-key", "your_api_key", "YOUR_API_KEY",
        "your-secret", "your_secret", "YOUR_SECRET",
        "example", "EXAMPLE", "sample", "SAMPLE",
        "test-key", "test_key", "TEST_KEY",
        "dummy", "DUMMY", "placeholder", "PLACEHOLDER",
        "xxx", "XXX", "***", "...",
    ]
    if any(ph in match.lower() for ph in placeholders):
        return True

    # Skip common variable names that match patterns but aren't secrets
    if rule_name == "Generic API Key":
        safe_patterns = ["api_key_id", "api_key_name", "api_key_prefix", "api_key_header"]
        if any(sp in match.lower() for sp in safe_patterns):
            return True

    # Skip documentation examples
    if "example" in match.lower() or "sample" in match.lower():
        return True

    return False


def scan_vulnerability_patterns(file_path: Path) -> list[dict]:
    """Scan for common vulnerability patterns in code."""
    findings = []
    ext = file_path.suffix

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
    except (IOError, OSError):
        return findings

    vuln_rules = get_vulnerability_rules(ext)

    for rule in vuln_rules:
        pattern = rule["pattern"]
        for line_num, line in enumerate(lines, 1):
            # Skip lines that appear to be rule definitions rather than actual code
            stripped = line.strip()
            if stripped.startswith('"pattern"') or stripped.startswith('"name"') or stripped.startswith('"description"'):
                continue
            # Skip markdown checkbox lines (documentation)
            if stripped.startswith('- [') and ('`' in stripped):
                continue
            if re.search(pattern, line):
                findings.append({
                    "file": str(file_path),
                    "line": line_num,
                    "type": "vulnerability",
                    "rule": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "match": line.strip()[:100],
                })

    return findings


def get_vulnerability_rules(ext: str) -> list[dict]:
    """Get vulnerability rules based on file extension."""
    common_rules = [
        {
            "name": "eval() usage",
            "pattern": r"(?<![\"\w])\beval\s*\(",
            "severity": "high",
            "description": "Dangerous eval() usage - can lead to RCE",
        },
        {
            "name": "exec() usage",
            "pattern": r"(?<![\"\w])\bexec\s*\(",
            "severity": "high",
            "description": "Dangerous exec() usage - can lead to RCE",
        },
        {
            "name": "Disabled SSL verification",
            "pattern": r"(?<![\"])(verify\s*=\s*False|InsecureRequestWarning|NODE_TLS_REJECT_UNAUTHORIZED|rejectUnauthorized\s*:\s*false)",
            "severity": "medium",
            "description": "SSL certificate verification is disabled",
        },
    ]

    python_rules = [
        {
            "name": "SQL Injection (string format)",
            "pattern": r"(execute|cursor\.execute|raw)\s*\(\s*['\"].*%s",
            "severity": "critical",
            "description": "Potential SQL injection via string formatting",
        },
        {
            "name": "pickle on untrusted data",
            "pattern": r"pickle\.loads?\s*\(",
            "severity": "high",
            "description": "Unsafe deserialization with pickle",
        },
        {
            "name": "shell=True in subprocess",
            "pattern": r"subprocess\.(call|run|Popen).*(shell\s*=\s*True)",
            "severity": "high",
            "description": "subprocess with shell=True is dangerous",
        },
        {
            "name": "DEBUG mode enabled",
            "pattern": r"(DEBUG\s*=\s*True|debug\s*=\s*True)",
            "severity": "medium",
            "description": "Debug mode enabled - may leak sensitive info",
        },
    ]

    js_rules = [
        {
            "name": "innerHTML assignment",
            "pattern": r"\.innerHTML\s*=",
            "severity": "medium",
            "description": "Potential XSS via innerHTML assignment",
        },
        {
            "name": "dangerouslySetInnerHTML",
            "pattern": r"dangerouslySetInnerHTML",
            "severity": "medium",
            "description": "React dangerouslySetInnerHTML usage",
        },
        {
            "name": "document.write",
            "pattern": r"document\.write\s*\(",
            "severity": "medium",
            "description": "document.write() can lead to XSS",
        },
    ]

    if ext in (".py", ".pyx"):
        return common_rules + python_rules
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        return common_rules + js_rules
    return common_rules


def scan_dependencies(root: str) -> list[dict]:
    """Scan project dependencies for known vulnerabilities."""
    findings = []
    root_path = Path(root)

    # Python pip audit
    if (root_path / "requirements.txt").exists() or (root_path / "pyproject.toml").exists():
        try:
            result = subprocess.run(
                ["pip", "audit", "--format=json"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get("vulnerabilities", []):
                        findings.append({
                            "file": str(root_path / "requirements.txt"),
                            "line": 0,
                            "type": "dependency",
                            "rule": "Known Vulnerable Dependency",
                            "severity": "high",
                            "description": f"Package {vuln.get('name', '?')} has known vulnerabilities",
                            "match": vuln.get("vulnerability_id", "unknown"),
                        })
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Node.js npm audit
    if (root_path / "package.json").exists() and (root_path / "package-lock.json").exists():
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout.strip():
                try:
                    audit_data = json.loads(result.stdout)
                    advisories = audit_data.get("advisories", {})
                    for adv_id, adv in advisories.items():
                        findings.append({
                            "file": str(root_path / "package.json"),
                            "line": 0,
                            "type": "dependency",
                            "rule": "NPM Audit Vulnerability",
                            "severity": adv.get("severity", "medium"),
                            "description": adv.get("overview", "Known vulnerability in dependency"),
                            "match": f"{adv.get('module_name', '?')} ({adv_id})",
                        })
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return findings


def scan_file_permissions(root: str) -> list[dict]:
    """Scan for files with overly permissive permissions."""
    findings = []
    root_path = Path(root)

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        if any(excl in str(file_path) for excl in EXCLUDE_PATHS):
            continue

        try:
            stat = file_path.stat()
            mode = stat.st_mode
            # Check if file is world-writable
            if mode & 0o002:
                findings.append({
                    "file": str(file_path),
                    "line": 0,
                    "type": "permission",
                    "rule": "World-writable file",
                    "severity": "low",
                    "description": "File is writable by all users",
                    "match": f"permissions: {oct(mode & 0o777)}",
                })
        except (OSError, IOError):
            continue

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python security_scan.py <project_root>")
        sys.exit(1)

    root = sys.argv[1]
    root_path = Path(root)

    if not root_path.exists():
        print(json.dumps({"error": f"Path not found: {root}"}, indent=2))
        sys.exit(1)

    all_findings = []

    # Walk through project files
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        if not should_scan_file(file_path):
            continue

        # Scan for secrets
        secret_findings = scan_file_for_secrets(file_path)
        all_findings.extend(secret_findings)

        # Scan for vulnerability patterns
        vuln_findings = scan_vulnerability_patterns(file_path)
        all_findings.extend(vuln_findings)

    # Scan dependencies
    dep_findings = scan_dependencies(root)
    all_findings.extend(dep_findings)

    # Scan file permissions (Unix only)
    if os.name != "nt":
        perm_findings = scan_file_permissions(root)
        all_findings.extend(perm_findings)

    # Determine overall status
    critical_count = sum(1 for f in all_findings if f["severity"] == "critical")
    high_count = sum(1 for f in all_findings if f["severity"] == "high")
    medium_count = sum(1 for f in all_findings if f["severity"] == "medium")
    low_count = sum(1 for f in all_findings if f["severity"] in ("low", "info"))

    # Security check passes if no critical/high findings
    passed = critical_count == 0 and high_count == 0

    output = {
        "project_root": root,
        "passed": passed,
        "total_files_scanned": sum(1 for f in root_path.rglob("*") if f.is_file() and should_scan_file(f)),
        "summary": {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total": len(all_findings),
        },
        "findings": sorted(all_findings, key=lambda x: ("critical", "high", "medium", "low", "info").index(x["severity"])),
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
