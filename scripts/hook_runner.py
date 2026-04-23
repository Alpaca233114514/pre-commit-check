#!/usr/bin/env python3
"""
Git hook runner for pre-commit-check.
Called by .git/hooks/pre-commit and .git/hooks/pre-push.
"""
import subprocess
import sys
import os

# Fix Windows terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def run_phase(script_name, repo_path, extra_args=None):
    """Run a check script and return (success, output)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)

    cmd = [sys.executable, script_path, repo_path]
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hook-type', required=True, choices=['pre-commit', 'pre-push'])
    parser.add_argument('repo_path', nargs='?', default='.')
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)

    print(f"\n{'='*60}")
    print(f"🔒 Pre-Commit Check [{args.hook_type}]")
    print(f"{'='*60}\n")

    # Phase 1: Code Tests (both hooks)
    print("📋 Phase 1: Running code tests...")
    ok, output = run_phase('run_tests.py', repo_path)
    if not ok:
        print("❌ Phase 1 FAILED\n")
        print(output)
        sys.exit(1)
    print("✅ Phase 1 PASSED\n")

    # Phase 2: Security Scan (both hooks)
    print("🔐 Phase 2: Running security scan...")
    ok, output = run_phase('security_scan.py', repo_path)
    if not ok:
        print("❌ Phase 2 FAILED\n")
        print(output)
        sys.exit(1)
    print("✅ Phase 2 PASSED\n")

    # Phase 3: Commit Info (pre-commit hook only)
    if args.hook_type == 'pre-commit':
        print("📝 Phase 3: Generating commit info...")
        ok, output = run_phase('generate_commit_info.py', repo_path)
        if ok:
            print("✅ Phase 3 PASSED\n")
            print("Suggested commit message:")
            print("-" * 40)
            print(output)
            print("-" * 40)
        else:
            print("⚠️  Phase 3 skipped or failed\n")

    print(f"\n{'='*60}")
    print(f"🎉 All checks passed! Proceeding with {args.hook_type}...")
    print(f"{'='*60}\n")
    sys.exit(0)


if __name__ == '__main__':
    main()
