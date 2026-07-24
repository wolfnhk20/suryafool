"""
check_env.py — Standalone environment status checker.

Runs all dependency checks for the current OS and prints a results table.
Makes no changes to the system.

Usage:
    python check_env.py
"""

import yaml
from bootstrap.checks import check_all
from bootstrap.platform import current_os, assert_supported


def main() -> None:
    os = assert_supported()

    with open("bootstrap/manifest.yaml") as f:
        manifest = yaml.safe_load(f)["dependencies"]

    print(f"\nSURYAFOOL — Environment Check")
    print(f"OS: {os.value}\n")

    results = check_all(manifest)

    col_w = max(len(name) for name in results) + 2
    print(f" {'Dependency':<{col_w}} {'Status':<10} Notes")
    print(f" {'─' * (col_w + 30)}")

    all_pass = True
    for name, result in results.items():
        status = "✓ PASS" if result.passed else "✗ FAIL"
        notes = "" if result.passed else (result.reason or "").splitlines()[0]
        print(f" {name:<{col_w}} {status:<10} {notes}")
        if not result.passed:
            all_pass = False

    print()
    if all_pass:
        print("✓ Environment ready.\n")
    else:
        print("✗ Some checks failed. Run `python -m bootstrap.agent` to remediate.\n")


if __name__ == "__main__":
    main()
