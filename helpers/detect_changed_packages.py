#!/usr/bin/env python3
"""Detect which packages changed relative to main."""

import json
import subprocess
import sys
from pathlib import Path


def git_show_file(ref: str, path: str) -> str | None:
    """Return file content from git reference."""
    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{path}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return None


def get_changed_files(base: str) -> list[str]:
    """Return list of files changed relative to base."""
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", base],
        text=True,
    )
    return diff.splitlines()


def get_merge_base() -> str:
    """Return merge base with origin/main."""
    return subprocess.check_output(
        ["git", "merge-base", "origin/main", "HEAD"],
        text=True,
    ).strip()


def detect_changed_packages(json_path: str) -> list[str]:
    """
    Determine which packages changed based on git diff.

    Args:
        json_path: Path to package-information.json

    Returns:
        List of changed package names
    """

    base = get_merge_base()

    with open(json_path) as f:
        current = json.load(f)

    previous_raw = git_show_file(base, json_path)
    previous = json.loads(previous_raw) if previous_raw else {"packages": []}

    current_packages = {p["name"]: p for p in current.get("packages", [])}
    previous_packages = {p["name"]: p for p in previous.get("packages", [])}

    changed_packages = set()

    # detect added / modified packages
    for name, pkg in current_packages.items():

        if name not in previous_packages:
            changed_packages.add(name)
            continue

        if pkg != previous_packages[name]:
            changed_packages.add(name)

    # detect directory changes
    changed_files = get_changed_files(base)

    for file in changed_files:
        path = Path(file)

        if path.parts and path.parts[0] in current_packages:
            changed_packages.add(path.parts[0])

    return sorted(changed_packages)


def main():

    if len(sys.argv) != 2:
        print("Usage: detect_changed_packages.py <json_path>", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]

    packages = detect_changed_packages(json_path)

    print(" ".join(packages))


if __name__ == "__main__":
    main()
