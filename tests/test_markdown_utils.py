"""Tests for monologue markdown parsing."""

from datetime import date
from pathlib import Path

import pytest

from monologue_tools.markdown_utils import (
    MonologueEntry,
    parse_markdown,
    write_metadata,
)


class TestParseMarkdownArchiveFormat:
    """Test parsing archive-format files with metadata headers."""

    def test_basic_archive(self):
        text = """\
Notion-Id: https://notion.so/filecoin/abc123
Last-Modified: 2024-04-24T04:30:51.468292+00:00
Subject: 2024-04-23: Numbers, TechSoup, Krazam

## Three Things I Did

Some content here.
"""
        entry = parse_markdown(text)
        assert entry.title == "Numbers, TechSoup, Krazam"
        assert entry.date == date(2024, 4, 23)
        assert entry.subject == "2024-04-23: Numbers, TechSoup, Krazam"
        assert entry.notion_id == "https://notion.so/filecoin/abc123"
        assert "Three Things I Did" in entry.body
        assert "Some content here." in entry.body

    def test_archive_preserves_metadata(self):
        text = """\
Notion-Id: https://notion.so/filecoin/abc123
Last-Modified: 2024-04-24T04:30:51+00:00
Subject: 2024-04-23: Test

## Body
"""
        entry = parse_markdown(text)
        assert entry.metadata["notion-id"] == "https://notion.so/filecoin/abc123"
        assert "last-modified" in entry.metadata

    def test_archive_no_title_after_date(self):
        text = """\
Subject: 2024-04-23

## Content
"""
        entry = parse_markdown(text)
        assert entry.date == date(2024, 4, 23)
        assert entry.title == ""


class TestParseMarkdownPlainFormat:
    """Test parsing plain markdown files with H1 headings."""

    def test_h1_with_date_and_title(self):
        text = """\
# 2025-02-07: My Great Post

## Working on

Something interesting.
"""
        entry = parse_markdown(text)
        assert entry.title == "My Great Post"
        assert entry.date == date(2025, 2, 7)
        assert entry.subject == "2025-02-07: My Great Post"
        assert "Working on" in entry.body
        assert entry.notion_id is None

    def test_h1_with_date_colon_title(self):
        text = "# 2025-01-15: Test, test, and test again\n\nBody here."
        entry = parse_markdown(text)
        assert entry.title == "Test, test, and test again"
        assert entry.date == date(2025, 1, 15)

    def test_h1_without_date(self):
        text = "# My Post Without A Date\n\nSome body text."
        entry = parse_markdown(text)
        assert entry.title == "My Post Without A Date"
        assert entry.date == date.today()
        assert "Some body text." in entry.body

    def test_body_excludes_h1(self):
        text = "# 2025-02-07: Title\n\n## Section\n\nContent"
        entry = parse_markdown(text)
        assert not entry.body.startswith("# ")
        assert "## Section" in entry.body


class TestParseMarkdownEdgeCases:
    """Test edge cases in markdown parsing."""

    def test_no_heading(self):
        text = "Just some text without any heading."
        entry = parse_markdown(text)
        assert entry.title == "Untitled"
        assert entry.body == text

    def test_empty_string(self):
        text = ""
        entry = parse_markdown(text)
        assert entry.title == "Untitled"

    def test_date_from_filename(self):
        text = "Just body text."
        entry = parse_markdown(text, source_path=Path("2025-02-07-my-post.md"))
        assert entry.date == date(2025, 2, 7)

    def test_source_path_preserved(self):
        text = "# 2025-02-07: Test\n\nBody"
        path = Path("/some/path/test.md")
        entry = parse_markdown(text, source_path=path)
        assert entry.source_path == path


class TestMonologueEntry:
    """Test MonologueEntry dataclass."""

    def test_date_str(self):
        entry = MonologueEntry(
            title="Test",
            date=date(2025, 2, 7),
            subject="2025-02-07: Test",
            body="Body",
        )
        assert entry.date_str == "2025-02-07"


class TestWriteMetadata:
    """Test writing metadata back to files."""

    def test_write_to_plain_markdown(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text("# 2025-02-07: My Post\n\n## Section\n\nContent here.\n")

        write_metadata(f, {"notion-id": "https://notion.so/abc123"})

        result = f.read_text()
        assert "Notion-Id: https://notion.so/abc123" in result
        assert "Subject: 2025-02-07: My Post" in result
        assert "## Section" in result
        assert "Content here." in result
        # Should NOT contain the H1 in the body
        assert "# 2025-02-07" not in result.split("\n\n", 1)[1]

    def test_write_to_existing_metadata(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text(
            "Notion-Id: https://notion.so/old-id\n"
            "Subject: 2025-02-07: My Post\n"
            "\n"
            "## Section\n\nContent.\n"
        )

        write_metadata(f, {"buttondown-id": "email-uuid-123"})

        result = f.read_text()
        # Existing metadata preserved
        assert "Notion-Id: https://notion.so/old-id" in result
        assert "Subject: 2025-02-07: My Post" in result
        # New metadata added
        assert "Buttondown-Id: email-uuid-123" in result
        # Body preserved
        assert "## Section" in result

    def test_overwrites_existing_key(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text(
            "Notion-Id: https://notion.so/old-id\nSubject: 2025-02-07: Test\n\nBody.\n"
        )

        write_metadata(f, {"notion-id": "https://notion.so/new-id"})

        result = f.read_text()
        assert "https://notion.so/new-id" in result
        assert "https://notion.so/old-id" not in result

    def test_roundtrip_preserves_body(self, tmp_path):
        f = tmp_path / "post.md"
        body = "## Working on\n\nSomething with **bold** and [links](http://example.com).\n\n## Thinking about\n\nMore stuff."
        f.write_text(f"# 2025-02-07: Test Post\n\n{body}\n")

        write_metadata(f, {"slack-ts": "123.456"})

        entry = parse_markdown(f.read_text())
        assert "Working on" in entry.body
        assert "**bold**" in entry.body
        assert "[links](http://example.com)" in entry.body
        assert "Thinking about" in entry.body

    def test_slack_metadata_keys(self, tmp_path):
        f = tmp_path / "post.md"
        f.write_text("Subject: 2025-02-07: Test\n\nBody.\n")

        write_metadata(f, {"slack-ts": "123.456", "slack-channel": "#monologue-danny"})

        result = f.read_text()
        assert "Slack-Ts: 123.456" in result
        assert "Slack-Channel: #monologue-danny" in result
