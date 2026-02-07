"""Parse monologue markdown files."""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class MonologueEntry:
    """A parsed monologue entry."""

    title: str  # Just the title part (e.g., "Numbers, TechSoup, Krazam")
    date: date  # The date
    subject: str  # Full subject line (e.g., "2024-04-23: Numbers, TechSoup, Krazam")
    body: str  # Markdown body content (after the H1/metadata header)
    source_path: Path | None = None
    notion_id: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def date_str(self) -> str:
        return self.date.isoformat()


def parse_markdown_file(path: Path) -> MonologueEntry:
    """Parse a markdown file into a MonologueEntry.

    Supports two formats:
    1. Archive format with metadata headers (Notion-Id, Subject, etc.)
    2. Plain markdown with an H1 containing a date
    """
    text = path.read_text()
    return parse_markdown(text, source_path=path)


def parse_markdown(text: str, source_path: Path | None = None) -> MonologueEntry:
    """Parse markdown text into a MonologueEntry."""
    lines = text.split("\n")

    # Try archive format first (metadata headers at top)
    metadata = {}
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            break
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            if key.lower() in (
                "notion-id",
                "last-modified",
                "subject",
                "buttondown-id",
            ):
                metadata[key.lower()] = value.strip()
            else:
                break  # Not a metadata line
        else:
            break

    if "subject" in metadata:
        subject = metadata["subject"]
        entry_date, title = _parse_date_title(subject)
        body = "\n".join(lines[body_start:]).strip()
        return MonologueEntry(
            title=title,
            date=entry_date,
            subject=subject,
            body=body,
            source_path=source_path,
            notion_id=metadata.get("notion-id"),
            metadata=metadata,
        )

    # Plain markdown format - look for H1 with date
    for i, line in enumerate(lines):
        if line.startswith("# "):
            heading = line[2:].strip()
            entry_date, title = _parse_date_title(heading)
            subject = f"{entry_date.isoformat()}: {title}" if title else heading
            body = "\n".join(lines[i + 1 :]).strip()
            return MonologueEntry(
                title=title,
                date=entry_date,
                subject=subject,
                body=body,
                source_path=source_path,
            )

    # No H1 found - use entire content as body, try to get date from filename
    entry_date = date.today()
    if source_path:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", source_path.stem)
        if date_match:
            entry_date = date.fromisoformat(date_match.group(1))

    return MonologueEntry(
        title="Untitled",
        date=entry_date,
        subject=f"{entry_date.isoformat()}: Untitled",
        body=text.strip(),
        source_path=source_path,
    )


def _parse_date_title(text: str) -> tuple[date, str]:
    """Extract date and title from a string like '2024-04-23: Numbers, TechSoup'."""
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if date_match:
        entry_date = date.fromisoformat(date_match.group(1))
        # Title is everything after the date, stripping leading ': '
        remainder = text[date_match.end() :].lstrip(": ").strip()
        return entry_date, remainder
    return date.today(), text.strip()
