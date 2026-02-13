#!/usr/bin/env python3
"""Parse package-information.json and output GitHub Actions matrix format."""

import json
import sys
from pathlib import Path


def parse_packages(json_path: str, package_filter: str | None = None) -> dict:
    """
    Parse package-information.json and return GitHub Actions matrix.

    Args:
        json_path: Path to package-information.json
        package_filter: Optional package name to filter (for manual dispatch)

    Returns:
        Dictionary with 'include' key containing list of matrix entries
    """
    with open(json_path) as f:
        data = json.load(f)

    urgap_version = data.get("urgap", "latest")
    packages = data.get("packages", [])

    # Get repository root (parent of helpers directory)
    repo_root = Path(json_path).parent

    matrix_include = []
    errors = []

    for package in packages:
        name = package["name"]

        # Skip if filter specified and doesn't match
        if package_filter and name != package_filter:
            continue

        # Validation: check package directory exists
        package_dir = repo_root / name
        if not package_dir.is_dir():
            errors.append(f"Package directory not found: {package_dir}")
            continue

        # Validation: check Dockerfile exists (handle custom dockerfile field)
        dockerfile_name = package.get("dockerfile", "Dockerfile")
        dockerfile_path = package_dir / dockerfile_name
        if not dockerfile_path.is_file():
            errors.append(f"Dockerfile not found: {dockerfile_path}")
            continue

        versions = package.get("versions", [])

        # Validation: check versions list is non-empty
        if not versions:
            errors.append(f"Package '{name}' has empty versions list")
            continue

        base_image = package.get("base_image", "")
        separate_venv = package.get("separate_venv", False)

        # Determine which version gets the 'latest' tag
        latest_version = versions[-1] if versions else None

        for version in versions:
            # Build base image with version if it ends with ':'
            resolved_base_image = base_image
            if base_image and base_image.endswith(":"):
                resolved_base_image = f"{base_image}{version}"

            entry = {
                "name": name,
                "version": version,
                "base_image": resolved_base_image,
                "separate_venv": str(separate_venv).lower(),
                "urgap_version": urgap_version,
                "is_latest": "true" if version == latest_version else "false",
            }
            matrix_include.append(entry)

    # Fail fast if validation errors found
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    return {"include": matrix_include}


def main():
    if len(sys.argv) < 2:
        print("Usage: parse_packages.py <json_path> [package_filter]", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    package_filter = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(json_path).exists():
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    matrix = parse_packages(json_path, package_filter)

    # Output for GitHub Actions
    print(json.dumps(matrix))


if __name__ == "__main__":
    main()
