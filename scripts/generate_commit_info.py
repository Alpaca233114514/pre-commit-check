#!/usr/bin/env python3
"""
Generate structured git commit information including:
- Conventional commit message based on git diff analysis
- Changes summary (files, insertions, deletions)
- Breaking change detection
- Scope auto-detection
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def get_git_diff(repo: str, staged: bool = True) -> str:
    """Get git diff output."""
    cmd = ["git", "-C", repo, "diff", "--stat"]
    if staged:
        cmd.append("--cached")
    else:
        cmd.append("HEAD")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def get_git_diff_files(repo: str, staged: bool = True) -> list[dict]:
    """Get list of changed files with status."""
    cmd = ["git", "-C", repo, "diff", "--name-status"]
    if staged:
        cmd.append("--cached")
    else:
        cmd.append("HEAD")

    files = []
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    files.append({
                        "status": status,
                        "path": filepath,
                    })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return files


def get_git_stats(repo: str, staged: bool = True) -> dict:
    """Get diff statistics (insertions, deletions)."""
    cmd = ["git", "-C", repo, "diff", "--shortstat"]
    if staged:
        cmd.append("--cached")
    else:
        cmd.append("HEAD")

    stats = {
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0,
    }

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            text = result.stdout.strip()
            # Parse: "X files changed, Y insertions(+), Z deletions(-)"
            m = re.search(r'(\d+)\s+file', text)
            if m:
                stats["files_changed"] = int(m.group(1))
            m = re.search(r'(\d+)\s+insertion', text)
            if m:
                stats["insertions"] = int(m.group(1))
            m = re.search(r'(\d+)\s+deletion', text)
            if m:
                stats["deletions"] = int(m.group(1))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return stats


def detect_scope(files: list[dict]) -> str | None:
    """Auto-detect scope from changed file paths."""
    path_segments = []
    for f in files:
        path = f["path"]
        parts = Path(path).parts
        if len(parts) > 1:
            # Skip common root directories
            first_dir = parts[0]
            if first_dir not in ("src", "app", "lib", "packages", "apps", "tools"):
                path_segments.append(first_dir)
            elif len(parts) > 2:
                path_segments.append(parts[1])
        else:
            # For root-level files, use file name without extension
            name = Path(path).stem
            if name:
                path_segments.append(name)

    if not path_segments:
        return None

    # Find most common segment
    from collections import Counter
    counter = Counter(path_segments)
    most_common = counter.most_common(1)[0][0]

    # Normalize: lowercase, remove special chars
    scope = re.sub(r'[^a-zA-Z0-9_-]', '', most_common).lower()
    return scope if scope else None


def detect_commit_type(files: list[dict], diff_stat: str) -> str:
    """Auto-detect commit type from changed files and diff."""
    paths = " ".join(f["path"] for f in files)
    path_lower = paths.lower()

    # Check for test files
    if any(p in path_lower for p in ("test", "spec", "__tests__", ".test.", ".spec.")):
        # If only test files, it's a test commit
        if all(any(t in f["path"].lower() for t in ("test", "spec", "__tests__", ".test.", ".spec.")) for f in files):
            return "test"

    # Check for documentation
    if any(p in path_lower for p in ("readme", "docs/", "doc/", "documentation", ".md", "changelog", "license")):
        doc_only = all(
            any(t in f["path"].lower() for t in ("readme", "docs/", "doc/", "documentation", ".md", "changelog", "license"))
            for f in files
        )
        if doc_only:
            return "docs"

    # Check for CI/CD
    if any(p in path_lower for p in (".github/", ".gitlab-ci", "dockerfile", "docker", "jenkins", ".circleci", "terraform", ".tf")):
        ci_only = all(
            any(t in f["path"].lower() for t in (".github/", ".gitlab-ci", "dockerfile", "docker", "jenkins", ".circleci", "terraform", ".tf"))
            for f in files
        )
        if ci_only:
            return "ci"

    # Check for dependency/config changes
    if any(p in path_lower for p in ("package.json", "requirements.txt", "cargo.toml", "go.mod", "pom.xml", "gemfile", "composer.json", ".gitignore", ".editorconfig", ".eslintrc", "tsconfig")):
        config_only = all(
            any(t in f["path"].lower() for t in ("package.json", "requirements.txt", "cargo.toml", "go.mod", "pom.xml", "gemfile", "composer.json", ".gitignore", ".editorconfig", ".eslintrc", "tsconfig"))
            for f in files
        )
        if config_only:
            return "chore"

    # Default to feat if new files are added, refactor if mostly modifications
    added = sum(1 for f in files if f["status"] == "A")
    modified = sum(1 for f in files if f["status"] == "M")
    deleted = sum(1 for f in files if f["status"] == "D")

    if deleted > 0 and modified == 0 and added == 0:
        return "chore"  # Removal-only changes

    # Check for breaking changes in diff
    if diff_stat and any(kw in diff_stat for kw in ("BREAKING", "breaking change", "!:")):
        return "feat"  # Marked as breaking, likely a feature change

    return "feat" if added >= modified else "refactor"


def detect_breaking_changes(files: list[dict], repo: str, staged: bool = True) -> list[str]:
    """Detect potential breaking changes from diff content."""
    breaking_indicators = []

    # Get full diff for analysis
    cmd = ["git", "-C", repo, "diff"]
    if staged:
        cmd.append("--cached")
    else:
        cmd.append("HEAD")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            diff = result.stdout
            # Check for common breaking change patterns
            if re.search(r'[-+]\s*(class|def|function)\s+\w+.*\(.*\)', diff):
                # Signature changes
                breaking_indicators.append("Function/method signature changes detected")
            if "BREAKING" in diff or "breaking change" in diff.lower():
                breaking_indicators.append("BREAKING CHANGE marker found in diff")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return breaking_indicators


def generate_description(files: list[dict], commit_type: str) -> str:
    """Generate a brief description based on changes."""
    if not files:
        return "update project files"

    # Group files by directory
    dirs = {}
    for f in files:
        dir_name = str(Path(f["path"]).parent)
        if dir_name == ".":
            dir_name = "root"
        dirs[dir_name] = dirs.get(dir_name, 0) + 1

    # Generate description
    statuses = {}
    for f in files:
        status = f["status"]
        if status == "A":
            statuses["add"] = statuses.get("add", 0) + 1
        elif status == "M":
            statuses["modify"] = statuses.get("modify", 0) + 1
        elif status == "D":
            statuses["delete"] = statuses.get("delete", 0) + 1
        elif status.startswith("R"):
            statuses["rename"] = statuses.get("rename", 0) + 1

    action = "update"
    if "add" in statuses and "modify" not in statuses and "delete" not in statuses:
        action = "add"
    elif "delete" in statuses and "modify" not in statuses and "add" not in statuses:
        action = "remove"
    elif "rename" in statuses:
        action = "rename"

    # Determine target
    if len(dirs) == 1:
        target = list(dirs.keys())[0]
        if target == "root":
            target = "files"
    else:
        # Find most changed area
        max_dir = max(dirs, key=dirs.get)
        target = max_dir if max_dir != "root" else "multiple components"

    type_actions = {
        "feat": "add",
        "fix": "fix",
        "docs": "update documentation for",
        "style": "format code in",
        "refactor": "refactor",
        "test": "add tests for",
        "chore": "update configuration for",
        "perf": "optimize performance of",
        "ci": "update CI for",
        "build": "update build for",
    }

    action = type_actions.get(commit_type, action)

    return f"{action} {target}"


def generate_commit_message(repo: str, staged: bool = True) -> dict:
    """Generate a conventional commit message from git diff."""
    files = get_git_diff_files(repo, staged)
    if not files:
        return {
            "error": "No changes detected. Stage files with 'git add' or use --unstaged.",
        }

    stats = get_git_stats(repo, staged)
    diff_stat = get_git_diff(repo, staged)
    scope = detect_scope(files)
    commit_type = detect_commit_type(files, diff_stat)
    breaking = detect_breaking_changes(files, repo, staged)
    description = generate_description(files, commit_type)

    # Build commit message
    scope_str = f"({scope})" if scope else ""
    breaking_marker = "!" if breaking else ""

    short_message = f"{commit_type}{scope_str}{breaking_marker}: {description}"

    # Truncate if too long (conventional commits recommends 50 chars for subject)
    if len(short_message) > 72:
        short_message = short_message[:69] + "..."

    # Build body
    body_lines = [
        f"Files changed: {stats['files_changed']}",
        f"Insertions: +{stats['insertions']}",
        f"Deletions: -{stats['deletions']}",
    ]

    if breaking:
        body_lines.append("")
        body_lines.append("BREAKING CHANGES:")
        for b in breaking:
            body_lines.append(f"- {b}")

    # File summary
    body_lines.append("")
    body_lines.append("Changed files:")
    for f in files[:20]:  # Limit to 20 files
        status_map = {
            "A": "added",
            "M": "modified",
            "D": "deleted",
            "R": "renamed",
            "C": "copied",
            "U": "updated",
        }
        status_label = status_map.get(f["status"][0], f["status"])
        body_lines.append(f"- [{status_label}] {f['path']}")

    if len(files) > 20:
        body_lines.append(f"- ... and {len(files) - 20} more files")

    body = "\n".join(body_lines)

    return {
        "type": commit_type,
        "scope": scope,
        "description": description,
        "breaking": len(breaking) > 0,
        "breaking_details": breaking,
        "short_message": short_message,
        "body": body,
        "stats": stats,
        "files_changed": len(files),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate structured git commit information")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path")
    parser.add_argument("--unstaged", action="store_true", help="Use unstaged changes instead of staged")
    parser.add_argument("--type-override", help="Override commit type")
    parser.add_argument("--scope-override", help="Override scope")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()

    staged = not args.unstaged
    result = generate_commit_message(args.repo, staged)

    if "error" in result:
        print(json.dumps(result, indent=2))
        sys.exit(1)

    # Apply overrides
    if args.type_override:
        result["type"] = args.type_override
        result["short_message"] = result["short_message"].replace(result["short_message"].split("(")[0], args.type_override, 1)

    if args.scope_override:
        old_scope = result.get("scope", "")
        result["scope"] = args.scope_override
        if old_scope:
            result["short_message"] = result["short_message"].replace(f"({old_scope})", f"({args.scope_override})")
        else:
            # Insert scope
            parts = result["short_message"].split(": ", 1)
            if len(parts) == 2:
                result["short_message"] = f"{parts[0]}({args.scope_override}): {parts[1]}"

    if args.format == "text":
        print(result["short_message"])
        print()
        print(result["body"])
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
