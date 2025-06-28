#!/usr/bin/env python
"""Pre-commit hook to prevent committing internal Notion URLs."""

import sys
import re

# Pattern to match internal Notion URLs
# Matches: https://notion.so/filecoin/... or https://www.notion.so/filecoin/...
NOTION_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?notion\.so/filecoin/[a-zA-Z0-9\-]+(?:-[a-f0-9]{32})?",
    re.IGNORECASE,
)

# Allowed patterns (for documentation/examples)
ALLOWED_PATTERNS = [
    # Example URLs in documentation
    r"notion\.so/filecoin/\[32-char-hex-id\]",
    # Fake/test URLs
    r"notion\.so/filecoin/abcdef123456abcdef123456abcdef12",
    # Generic example URLs
    r"notion\.so/filecoin/example-",
]

ALLOWED_REGEX = re.compile("|".join(ALLOWED_PATTERNS), re.IGNORECASE)


def check_file(filepath):
    """Check a single file for internal Notion URLs."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        # Skip binary files or files that can't be read
        return True

    # Find all Notion URLs
    matches = NOTION_URL_PATTERN.findall(content)

    # Filter out allowed patterns
    problematic_urls = []
    for url in matches:
        if not ALLOWED_REGEX.search(url):
            problematic_urls.append(url)

    if problematic_urls:
        print(f"\n❌ Found internal Notion URLs in {filepath}:")
        for url in set(problematic_urls):  # Use set to remove duplicates
            print(f"   {url}")
        return False

    return True


def main():
    """Check all files passed as arguments."""
    if len(sys.argv) < 2:
        print("No files to check")
        return 0

    failed_files = []

    for filepath in sys.argv[1:]:
        if not check_file(filepath):
            failed_files.append(filepath)

    if failed_files:
        print(f"\n⚠️  Found internal Notion URLs in {len(failed_files)} file(s)")
        print("Please remove or replace these URLs before committing.")
        print("\nHint: You can use placeholder URLs like:")
        print("  - https://notion.so/filecoin/[32-char-hex-id]")
        print("  - https://notion.so/filecoin/example-page-title")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
