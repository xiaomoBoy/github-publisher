#!/usr/bin/env python3
"""Print a friendly greeting."""

import sys


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "world"
    print(f"Hello, {name}!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
