"""Parse monologue markdown files."""

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

# Old email-header keys (for backward compat with archive files)
_LEGACY_KEYS = frozenset(
    {
        "notion-id",
        "last-modified",
        "subject",
        "buttondown-id",
        "slack-ts",
        "slack-channel",
    }
)

# Map legacy hyphenated keys to new underscore keys
_LEGACY_KEY_MAP = {
    "notion-id": "notion_id",
    "last-modified": "last_modified",
    "buttondown-id": "buttondown_id",
    "slack-ts": "slack_ts",
    "slack-channel": "slack_channel",
}


@dataclass
class MonologueEntry:
    """A parsed monologue entry."""

    title: str  # Just the title part (e.g., "Numbers, TechSoup, Krazam")
    date: date  # The date
    subject: str  # Full subject line (e.g., "2024-04-23: Numbers, TechSoup, Krazam")
    body: str  # Markdown body content (after the H1/frontmatter)
    source_path: Path | None = None
    notion_id: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def date_str(self) -> str:
        return self.date.isoformat()


def parse_markdown_file(path: Path) -> MonologueEntry:
    """Parse a markdown file into a MonologueEntry.

    Supports three formats:
    1. YAML frontmatter (--- delimited)
    2. Legacy email-style metadata headers (Notion-Id, Subject, etc.)
    3. Plain markdown with an H1 containing a date
    """
    text = path.read_text()
    return parse_markdown(text, source_path=path)


def parse_markdown(text: str, source_path: Path | None = None) -> MonologueEntry:
    """Parse markdown text into a MonologueEntry."""
    lines = text.split("\n")

    # Try YAML frontmatter first (--- delimited)
    if lines and lines[0].strip() == "---":
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is not None:
            frontmatter_text = "\n".join(lines[1:end])
            meta = yaml.safe_load(frontmatter_text) or {}
            body = "\n".join(lines[end + 1 :]).strip()

            title = str(meta.get("title", ""))
            entry_date = meta.get("date")
            if isinstance(entry_date, date):
                pass  # yaml.safe_load parses dates natively
            elif isinstance(entry_date, str):
                entry_date = date.fromisoformat(entry_date)
            else:
                entry_date = date.today()

            subject = (
                f"{entry_date.isoformat()}: {title}"
                if title
                else entry_date.isoformat()
            )

            return MonologueEntry(
                title=title,
                date=entry_date,
                subject=subject,
                body=body,
                source_path=source_path,
                notion_id=meta.get("notion_id"),
                metadata=meta,
            )

    # Try legacy email-header format
    metadata = {}
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            break
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            if key.lower() in _LEGACY_KEYS:
                # Convert to new underscore key names
                new_key = _LEGACY_KEY_MAP.get(key.lower(), key.lower())
                metadata[new_key] = value.strip()
            else:
                break  # Not a metadata line
        else:
            break

    if "subject" in metadata:
        subject = metadata.pop("subject")
        entry_date, title = _parse_date_title(subject)
        body = "\n".join(lines[body_start:]).strip()
        return MonologueEntry(
            title=title,
            date=entry_date,
            subject=subject,
            body=body,
            source_path=source_path,
            notion_id=metadata.get("notion_id"),
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


def write_metadata(path: Path, updates: dict[str, str]) -> None:
    """Update YAML frontmatter in a markdown file, preserving body content.

    If the file already has YAML frontmatter, it is updated/extended.
    If the file has legacy email headers, they are converted to YAML frontmatter.
    If the file is plain markdown (H1 heading), frontmatter is prepended.
    """
    text = path.read_text()
    entry = parse_markdown(text, source_path=path)

    # Start with existing metadata
    meta = dict(entry.metadata)

    # Always ensure title and date are in the frontmatter
    if "title" not in meta:
        meta["title"] = entry.title
    if "date" not in meta:
        meta["date"] = entry.date

    # Apply updates
    for k, v in updates.items():
        meta[k] = v

    # Order keys nicely for the YAML output
    key_order = [
        "title",
        "date",
        "notion_id",
        "buttondown_id",
        "slack_ts",
        "slack_channel",
        "last_modified",
    ]
    ordered_meta = {}
    for key in key_order:
        if key in meta:
            ordered_meta[key] = meta[key]
    for key, value in meta.items():
        if key not in ordered_meta:
            ordered_meta[key] = value

    frontmatter = yaml.dump(
        ordered_meta,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()

    path.write_text(f"---\n{frontmatter}\n---\n\n{entry.body}\n")
