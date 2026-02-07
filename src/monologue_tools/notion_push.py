"""Push markdown content to Notion as a page."""

import re

from notion_client import Client

BATCH_SIZE = 100


def parse_rich_text(text: str) -> list[dict]:
    """Parse inline markdown into Notion rich_text array.

    Handles **bold**, *italic*, _italic_, `code`, and [text](url).
    """
    if not text:
        return []

    # Pattern matches inline markdown formatting tokens in order of priority
    pattern = re.compile(
        r"\*\*(.+?)\*\*"  # **bold**
        r"|`(.+?)`"  # `code`
        r"|\[([^\]]+)\]\(([^)]+)\)"  # [text](url)
        r"|\*(.+?)\*"  # *italic*
        r"|_(.+?)_"  # _italic_
    )

    result = []
    pos = 0
    for m in pattern.finditer(text):
        # Add any plain text before this match
        if m.start() > pos:
            result.append(
                {
                    "type": "text",
                    "text": {"content": text[pos : m.start()]},
                }
            )

        if m.group(1) is not None:
            # Bold
            result.append(
                {
                    "type": "text",
                    "text": {"content": m.group(1)},
                    "annotations": {"bold": True},
                }
            )
        elif m.group(2) is not None:
            # Code
            result.append(
                {
                    "type": "text",
                    "text": {"content": m.group(2)},
                    "annotations": {"code": True},
                }
            )
        elif m.group(3) is not None:
            # Link
            result.append(
                {
                    "type": "text",
                    "text": {
                        "content": m.group(3),
                        "link": {"url": m.group(4)},
                    },
                }
            )
        elif m.group(5) is not None:
            # Italic (star)
            result.append(
                {
                    "type": "text",
                    "text": {"content": m.group(5)},
                    "annotations": {"italic": True},
                }
            )
        elif m.group(6) is not None:
            # Italic (underscore)
            result.append(
                {
                    "type": "text",
                    "text": {"content": m.group(6)},
                    "annotations": {"italic": True},
                }
            )

        pos = m.end()

    # Add remaining plain text
    if pos < len(text):
        result.append({"type": "text", "text": {"content": text[pos:]}})

    return result


def markdown_to_notion_blocks(markdown: str) -> list[dict]:
    """Convert markdown to a list of Notion API block objects."""
    lines = markdown.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Blank line - skip
        if not line.strip():
            i += 1
            continue

        # H1 - skip (title is separate)
        if line.startswith("# ") and not line.startswith("## "):
            i += 1
            continue

        # Heading 2
        if line.startswith("## "):
            blocks.append(
                {
                    "type": "heading_2",
                    "heading_2": {"rich_text": parse_rich_text(line[3:].strip())},
                }
            )
            i += 1
            continue

        # Heading 3
        if line.startswith("### "):
            blocks.append(
                {
                    "type": "heading_3",
                    "heading_3": {"rich_text": parse_rich_text(line[4:].strip())},
                }
            )
            i += 1
            continue

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append(
                {
                    "type": "code",
                    "code": {
                        "language": lang,
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "\n".join(code_lines)},
                            }
                        ],
                    },
                }
            )
            continue

        # Divider
        if line.strip() in ("---", "***", "___"):
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            blocks.append(
                {
                    "type": "quote",
                    "quote": {"rich_text": parse_rich_text(line[2:].strip())},
                }
            )
            i += 1
            continue

        # Bulleted list
        if re.match(r"^[-*] ", line):
            text = line[2:].strip()
            blocks.append(
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": parse_rich_text(text)},
                }
            )
            i += 1
            continue

        # Numbered list
        m = re.match(r"^\d+\. (.+)", line)
        if m:
            blocks.append(
                {
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": parse_rich_text(m.group(1).strip())
                    },
                }
            )
            i += 1
            continue

        # Paragraph: collect consecutive non-empty, non-special lines
        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if not next_line.strip():
                break
            if re.match(
                r"^(#{1,3} |[-*] |\d+\. |```|> |---$|___$|\*\*\*$)",
                next_line,
            ):
                break
            para_lines.append(next_line)
            i += 1

        blocks.append(
            {
                "type": "paragraph",
                "paragraph": {"rich_text": parse_rich_text(" ".join(para_lines))},
            }
        )

    return blocks


class NotionPublisher:
    """Publishes markdown content to Notion as a page."""

    def __init__(self, token: str, parent_page_id: str):
        self.client = Client(auth=token)
        self.parent_page_id = parent_page_id

    def publish(self, title: str, markdown_body: str) -> str:
        """Create a Notion page under parent_page_id and return the page URL.

        Handles >100 blocks by appending in batches (API limit).
        """
        blocks = markdown_to_notion_blocks(markdown_body)

        # First batch goes with the page creation (max 100)
        first_batch = blocks[:BATCH_SIZE]
        remaining = blocks[BATCH_SIZE:]

        response = self.client.pages.create(
            parent={"page_id": self.parent_page_id},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=first_batch,
        )

        # Append remaining blocks in batches of 100
        if remaining:
            page_id = response["id"]
        while remaining:
            batch = remaining[:BATCH_SIZE]
            remaining = remaining[BATCH_SIZE:]
            self.client.blocks.children.append(block_id=page_id, children=batch)

        return response["url"]

    def update(self, page_url: str, title: str, markdown_body: str) -> str:
        """Update an existing Notion page's title and content. Returns the page URL."""
        page_id = page_url_to_id(page_url)

        # Update title
        self.client.pages.update(
            page_id=page_id,
            properties={"title": {"title": [{"text": {"content": title}}]}},
        )

        # Delete all existing blocks
        existing = self.client.blocks.children.list(block_id=page_id)
        for block in existing["results"]:
            self.client.blocks.delete(block_id=block["id"])

        # Append new blocks in batches
        blocks = markdown_to_notion_blocks(markdown_body)
        while blocks:
            batch = blocks[:BATCH_SIZE]
            blocks = blocks[BATCH_SIZE:]
            self.client.blocks.children.append(block_id=page_id, children=batch)

        return page_url


def page_url_to_id(url: str) -> str:
    """Extract a Notion page ID from a URL.

    URLs look like: https://www.notion.so/Page-Title-abc123def456...
    or just: https://notion.so/workspace/abc123def456...
    The last 32 hex characters are the page ID.
    """
    # Strip query params and fragments
    path = url.split("?")[0].split("#")[0]
    # Find the last 32 hex chars
    match = re.search(r"([a-f0-9]{32})$", path.replace("-", ""))
    if match:
        hex_id = match.group(1)
        # Format as UUID: 8-4-4-4-12
        return (
            f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:]}"
        )
    raise ValueError(f"Cannot extract page ID from URL: {url}")
