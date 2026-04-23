#!/usr/bin/env python3
"""
Detect project type, language, and testing framework configuration.
Supports Python, Node.js, Go, Rust, Java, Ruby, PHP, and more.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def find_git_root(path: str = ".") -> str | None:
    """Find the git repository root."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def detect_language_configs(root: str) -> list[dict[str, Any]]:
    """Detect project languages and their test configurations."""
    root_path = Path(root)
    configs = []

    # Python detection
    if any(root_path.glob("*.py")) or (root_path / "requirements.txt").exists() or (root_path / "pyproject.toml").exists():
        python_config: dict[str, Any] = {
            "language": "python",
            "test_tools": [],
            "config_files": [],
        }
        if (root_path / "pytest.ini").exists() or (root_path / "pyproject.toml").exists():
            python_config["test_tools"].append("pytest")
        if (root_path / "setup.cfg").exists():
            python_config["config_files"].append("setup.cfg")
        if (root_path / "tox.ini").exists():
            python_config["test_tools"].append("tox")
        # Default to unittest if no specific tool found
        if not python_config["test_tools"]:
            python_config["test_tools"].append("unittest")
        configs.append(python_config)

    # Node.js detection
    if (root_path / "package.json").exists():
        node_config: dict[str, Any] = {
            "language": "nodejs",
            "test_tools": [],
            "config_files": ["package.json"],
        }
        pkg_json = root_path / "package.json"
        try:
            with open(pkg_json, "r") as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            if any("jest" in v for v in scripts.values()):
                node_config["test_tools"].append("jest")
            if any("mocha" in v for v in scripts.values()):
                node_config["test_tools"].append("mocha")
            if any("vitest" in v for v in scripts.values()):
                node_config["test_tools"].append("vitest")
            if any("cypress" in v for v in scripts.values()):
                node_config["test_tools"].append("cypress")
            if any("playwright" in v for v in scripts.values()):
                node_config["test_tools"].append("playwright")
            # Default detection from devDependencies
            dev_deps = pkg.get("devDependencies", {})
            if "jest" in dev_deps and "jest" not in node_config["test_tools"]:
                node_config["test_tools"].append("jest")
            if "mocha" in dev_deps and "mocha" not in node_config["test_tools"]:
                node_config["test_tools"].append("mocha")
            if "vitest" in dev_deps and "vitest" not in node_config["test_tools"]:
                node_config["test_tools"].append("vitest")
            if "cypress" in dev_deps and "cypress" not in node_config["test_tools"]:
                node_config["test_tools"].append("cypress")
        except (json.JSONDecodeError, IOError):
            pass
        if not node_config["test_tools"]:
            node_config["test_tools"].append("npm test")
        configs.append(node_config)

    # Go detection
    if any(root_path.rglob("*.go")) or (root_path / "go.mod").exists():
        configs.append({
            "language": "go",
            "test_tools": ["go test"],
            "config_files": ["go.mod"] if (root_path / "go.mod").exists() else [],
        })

    # Rust detection
    if (root_path / "Cargo.toml").exists():
        configs.append({
            "language": "rust",
            "test_tools": ["cargo test"],
            "config_files": ["Cargo.toml"],
        })

    # Java detection
    if any(root_path.rglob("*.java")) or (root_path / "pom.xml").exists() or (root_path / "build.gradle").exists():
        java_config: dict[str, Any] = {
            "language": "java",
            "test_tools": [],
            "config_files": [],
        }
        if (root_path / "pom.xml").exists():
            java_config["test_tools"].append("maven test")
            java_config["config_files"].append("pom.xml")
        if (root_path / "build.gradle").exists():
            java_config["test_tools"].append("gradle test")
            java_config["config_files"].append("build.gradle")
        if not java_config["test_tools"]:
            java_config["test_tools"].append("maven test")
        configs.append(java_config)

    # Ruby detection
    if any(root_path.rglob("*.rb")) or (root_path / "Gemfile").exists():
        configs.append({
            "language": "ruby",
            "test_tools": ["rspec", "minitest"],
            "config_files": ["Gemfile"],
        })

    # PHP detection
    if any(root_path.rglob("*.php")) or (root_path / "composer.json").exists():
        php_config: dict[str, Any] = {
            "language": "php",
            "test_tools": ["phpunit"],
            "config_files": [],
        }
        if (root_path / "phpunit.xml").exists() or (root_path / "phpunit.xml.dist").exists():
            php_config["config_files"].append("phpunit.xml")
        configs.append(php_config)

    # C# / .NET detection
    if any(root_path.rglob("*.cs")) or any(root_path.rglob("*.csproj")):
        configs.append({
            "language": "csharp",
            "test_tools": ["dotnet test"],
            "config_files": [],
        })

    return configs


def find_claude_md_equivalent(root: str) -> str | None:
    """Find CLAUDE.md or equivalent strictness configuration file."""
    root_path = Path(root)
    candidates = [
        "CLAUDE.md",
        "claude.md",
        "CLAUDE.txt",
        ".claude.md",
        "AGENT.md",
        "agent.md",
        ".agent.md",
        "CONTRIBUTING.md",
        "DEVELOPMENT.md",
        "DEV.md",
        "README.md",
    ]
    for candidate in candidates:
        if (root_path / candidate).exists():
            return str(root_path / candidate)
    return None


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    git_root = find_git_root(repo)

    if not git_root:
        print(json.dumps({"error": "Not a git repository"}, indent=2))
        sys.exit(1)

    languages = detect_language_configs(git_root)
    strictness_file = find_claude_md_equivalent(git_root)

    result = {
        "git_root": git_root,
        "languages": languages,
        "strictness_file": strictness_file,
        "has_strictness_config": strictness_file is not None,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
