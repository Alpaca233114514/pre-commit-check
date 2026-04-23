#!/usr/bin/env python3
"""
Run language-specific tests based on project detection results.
Supports multiple languages and test frameworks with exit code propagation.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: str, timeout: int = 300) -> dict:
    """Run a shell command and return structured result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "command": " ".join(cmd),
            "returncode": result.returncode,
            "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
            "stderr": result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr,
            "passed": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "passed": False,
        }
    except FileNotFoundError as e:
        return {
            "command": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command not found: {e}",
            "passed": False,
        }


def run_python_tests(root: str, tools: list[str]) -> list[dict]:
    """Run Python tests using detected tools."""
    results = []
    if "pytest" in tools:
        results.append(run_command(["python", "-m", "pytest", "-v", "--tb=short"], root))
    elif "tox" in tools:
        results.append(run_command(["tox"], root))
    elif "unittest" in tools:
        results.append(run_command(["python", "-m", "unittest", "discover", "-v"], root))
    return results


def run_nodejs_tests(root: str, tools: list[str]) -> list[dict]:
    """Run Node.js tests using detected tools."""
    results = []
    # Check package.json for test script first
    pkg_json = Path(root) / "package.json"
    if pkg_json.exists():
        try:
            import json
            with open(pkg_json) as f:
                pkg = json.load(f)
            if "scripts" in pkg and "test" in pkg["scripts"]:
                results.append(run_command(["npm", "test"], root))
                return results
        except (json.JSONDecodeError, IOError):
            pass
    # Fallback to detected tools
    for tool in tools:
        if tool in ("jest", "mocha", "vitest", "cypress", "playwright"):
            bin_path = Path(root) / "node_modules" / ".bin" / tool
            if bin_path.exists():
                results.append(run_command([str(bin_path)], root))
            else:
                results.append(run_command(["npx", tool], root))
    return results


def run_go_tests(root: str) -> list[dict]:
    """Run Go tests."""
    return [run_command(["go", "test", "-v", "./..."], root)]


def run_rust_tests(root: str) -> list[dict]:
    """Run Rust tests."""
    return [run_command(["cargo", "test"], root)]


def run_java_tests(root: str, tools: list[str]) -> list[dict]:
    """Run Java tests."""
    results = []
    if "maven test" in tools:
        results.append(run_command(["mvn", "test"], root))
    if "gradle test" in tools:
        results.append(run_command(["./gradlew", "test"] if (Path(root) / "gradlew").exists() else ["gradle", "test"], root))
    return results


def run_ruby_tests(root: str) -> list[dict]:
    """Run Ruby tests."""
    results = []
    if (Path(root) / "Gemfile").exists():
        results.append(run_command(["bundle", "exec", "rspec"], root))
    else:
        results.append(run_command(["rspec"], root))
    return results


def run_php_tests(root: str) -> list[dict]:
    """Run PHP tests."""
    results = []
    phpunit_path = Path(root) / "vendor" / "bin" / "phpunit"
    if phpunit_path.exists():
        results.append(run_command([str(phpunit_path)], root))
    else:
        results.append(run_command(["phpunit"], root))
    return results


def run_csharp_tests(root: str) -> list[dict]:
    """Run C# / .NET tests."""
    return [run_command(["dotnet", "test"], root)]


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <project_root> [language_config_json]")
        sys.exit(1)

    root = sys.argv[1]

    # Load language config if provided
    if len(sys.argv) >= 3:
        try:
            language_config = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON config"}, indent=2))
            sys.exit(1)
    else:
        # Auto-detect
        try:
            detect_result = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "detect_project.py"), root],
                capture_output=True,
                text=True,
                timeout=30,
            )
            project_info = json.loads(detect_result.stdout)
            language_config = project_info.get("languages", [])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            print(json.dumps({"error": f"Failed to auto-detect project: {e}"}, indent=2))
            sys.exit(1)

    all_results = []
    overall_passed = True

    for lang_info in language_config:
        language = lang_info.get("language", "")
        tools = lang_info.get("test_tools", [])

        if language == "python":
            results = run_python_tests(root, tools)
        elif language == "nodejs":
            results = run_nodejs_tests(root, tools)
        elif language == "go":
            results = run_go_tests(root)
        elif language == "rust":
            results = run_rust_tests(root)
        elif language == "java":
            results = run_java_tests(root, tools)
        elif language == "ruby":
            results = run_ruby_tests(root)
        elif language == "php":
            results = run_php_tests(root)
        elif language == "csharp":
            results = run_csharp_tests(root)
        else:
            continue

        for r in results:
            r["language"] = language
        all_results.extend(results)

        if any(not r["passed"] for r in results):
            overall_passed = False

    output = {
        "project_root": root,
        "overall_passed": overall_passed,
        "total_tests": len(all_results),
        "passed_tests": sum(1 for r in all_results if r["passed"]),
        "failed_tests": sum(1 for r in all_results if not r["passed"]),
        "results": all_results,
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if overall_passed else 1)


if __name__ == "__main__":
    main()
