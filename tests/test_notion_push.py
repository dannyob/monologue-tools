from unittest.mock import MagicMock, call, patch

import pytest

from monologue_tools.notion_push import (
    NotionPublisher,
    markdown_to_notion_blocks,
    page_url_to_id,
    parse_rich_text,
)


class TestParseRichText:
    def test_plain_text(self):
        result = parse_rich_text("hello world")
        assert result == [{"type": "text", "text": {"content": "hello world"}}]

    def test_bold(self):
        result = parse_rich_text("some **bold** text")
        assert result == [
            {"type": "text", "text": {"content": "some "}},
            {
                "type": "text",
                "text": {"content": "bold"},
                "annotations": {"bold": True},
            },
            {"type": "text", "text": {"content": " text"}},
        ]

    def test_italic_star(self):
        result = parse_rich_text("some *italic* text")
        assert result == [
            {"type": "text", "text": {"content": "some "}},
            {
                "type": "text",
                "text": {"content": "italic"},
                "annotations": {"italic": True},
            },
            {"type": "text", "text": {"content": " text"}},
        ]

    def test_italic_underscore(self):
        result = parse_rich_text("some _italic_ text")
        assert result == [
            {"type": "text", "text": {"content": "some "}},
            {
                "type": "text",
                "text": {"content": "italic"},
                "annotations": {"italic": True},
            },
            {"type": "text", "text": {"content": " text"}},
        ]

    def test_inline_code(self):
        result = parse_rich_text("some `code` text")
        assert result == [
            {"type": "text", "text": {"content": "some "}},
            {
                "type": "text",
                "text": {"content": "code"},
                "annotations": {"code": True},
            },
            {"type": "text", "text": {"content": " text"}},
        ]

    def test_link(self):
        result = parse_rich_text("click [here](https://example.com) now")
        assert result == [
            {"type": "text", "text": {"content": "click "}},
            {
                "type": "text",
                "text": {
                    "content": "here",
                    "link": {"url": "https://example.com"},
                },
            },
            {"type": "text", "text": {"content": " now"}},
        ]

    def test_empty_string(self):
        result = parse_rich_text("")
        assert result == []

    def test_multiple_inline_formats(self):
        result = parse_rich_text("**bold** and *italic*")
        assert result == [
            {
                "type": "text",
                "text": {"content": "bold"},
                "annotations": {"bold": True},
            },
            {"type": "text", "text": {"content": " and "}},
            {
                "type": "text",
                "text": {"content": "italic"},
                "annotations": {"italic": True},
            },
        ]


class TestMarkdownToNotionBlocks:
    def test_paragraph(self):
        blocks = markdown_to_notion_blocks("Hello world")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"] == [
            {"type": "text", "text": {"content": "Hello world"}}
        ]

    def test_heading_2(self):
        blocks = markdown_to_notion_blocks("## My Heading")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_2"
        assert blocks[0]["heading_2"]["rich_text"] == [
            {"type": "text", "text": {"content": "My Heading"}}
        ]

    def test_heading_3(self):
        blocks = markdown_to_notion_blocks("### Sub Heading")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_3"
        assert blocks[0]["heading_3"]["rich_text"] == [
            {"type": "text", "text": {"content": "Sub Heading"}}
        ]

    def test_bulleted_list(self):
        md = "- item one\n- item two"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[0]["bulleted_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "item one"}}
        ]
        assert blocks[1]["type"] == "bulleted_list_item"

    def test_bulleted_list_star(self):
        md = "* item one\n* item two"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_numbered_list(self):
        md = "1. first\n2. second"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "numbered_list_item"
        assert blocks[0]["numbered_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "first"}}
        ]

    def test_code_block(self):
        md = "```python\nprint('hello')\n```"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert blocks[0]["code"]["rich_text"] == [
            {"type": "text", "text": {"content": "print('hello')"}}
        ]

    def test_code_block_no_language(self):
        md = "```\nsome code\n```"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "plain text"

    def test_quote(self):
        blocks = markdown_to_notion_blocks("> This is a quote")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "quote"
        assert blocks[0]["quote"]["rich_text"] == [
            {"type": "text", "text": {"content": "This is a quote"}}
        ]

    def test_divider(self):
        blocks = markdown_to_notion_blocks("---")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "divider"
        assert blocks[0]["divider"] == {}

    def test_mixed_content(self):
        md = "## Title\n\nA paragraph.\n\n- item\n\n---\n\n> quote"
        blocks = markdown_to_notion_blocks(md)
        types = [b["type"] for b in blocks]
        assert types == [
            "heading_2",
            "paragraph",
            "bulleted_list_item",
            "divider",
            "quote",
        ]

    def test_multiline_paragraph(self):
        md = "Line one\nLine two\n\nNew paragraph"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "paragraph"
        # The first paragraph should contain both lines
        content = "".join(
            rt["text"]["content"] for rt in blocks[0]["paragraph"]["rich_text"]
        )
        assert "Line one" in content
        assert "Line two" in content
        assert blocks[1]["type"] == "paragraph"

    def test_h1_skipped(self):
        blocks = markdown_to_notion_blocks("# Top Level Heading")
        # H1 should be skipped since title is separate
        assert len(blocks) == 0

    def test_nested_bulleted_list(self):
        md = "- parent\n  - child one\n  - child two\n- sibling"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[0]["bulleted_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "parent"}}
        ]
        children = blocks[0]["bulleted_list_item"]["children"]
        assert len(children) == 2
        assert children[0]["type"] == "bulleted_list_item"
        assert children[0]["bulleted_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "child one"}}
        ]
        assert blocks[1]["bulleted_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "sibling"}}
        ]
        assert "children" not in blocks[1]["bulleted_list_item"]

    def test_nested_numbered_list(self):
        md = "1. first\n   1. sub one\n   2. sub two\n2. second"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "numbered_list_item"
        children = blocks[0]["numbered_list_item"]["children"]
        assert len(children) == 2
        assert children[0]["type"] == "numbered_list_item"
        assert blocks[1]["type"] == "numbered_list_item"

    def test_deeply_nested_list(self):
        md = "- a\n  - b\n    - c"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        children = blocks[0]["bulleted_list_item"]["children"]
        assert len(children) == 1
        grandchildren = children[0]["bulleted_list_item"]["children"]
        assert len(grandchildren) == 1
        assert grandchildren[0]["bulleted_list_item"]["rich_text"] == [
            {"type": "text", "text": {"content": "c"}}
        ]

    def test_mixed_nested_list_types(self):
        md = "- bullet\n  1. numbered child"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        children = blocks[0]["bulleted_list_item"]["children"]
        assert len(children) == 1
        assert children[0]["type"] == "numbered_list_item"

    def test_image(self):
        md = "![photo](https://example.com/img.png)"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "image"
        assert blocks[0]["image"]["type"] == "external"
        assert blocks[0]["image"]["external"]["url"] == "https://example.com/img.png"
        assert blocks[0]["image"]["caption"] == [
            {"type": "text", "text": {"content": "photo"}}
        ]

    def test_image_no_alt(self):
        md = "![](https://example.com/img.png)"
        blocks = markdown_to_notion_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "image"
        assert "caption" not in blocks[0]["image"]

    def test_image_not_absorbed_into_paragraph(self):
        md = "Some text.\n\n![pic](https://example.com/a.png)\n\nMore text."
        blocks = markdown_to_notion_blocks(md)
        types = [b["type"] for b in blocks]
        assert types == ["paragraph", "image", "paragraph"]


class TestNotionPublisher:
    @patch("monologue_tools.notion_push.Client")
    def test_publish_creates_page(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.return_value = {
            "url": "https://www.notion.so/test-page-abc123"
        }

        publisher = NotionPublisher(token="fake-token", parent_page_id="parent-id-123")
        url = publisher.publish("My Title", "Hello world")

        assert url == "https://www.notion.so/test-page-abc123"
        mock_client_cls.assert_called_once_with(auth="fake-token")
        mock_client.pages.create.assert_called_once()

        create_kwargs = mock_client.pages.create.call_args
        # Check parent
        assert create_kwargs.kwargs["parent"] == {"page_id": "parent-id-123"}
        # Check title property
        props = create_kwargs.kwargs["properties"]
        assert "title" in props
        assert props["title"]["title"][0]["text"]["content"] == "My Title"
        # Check children contain the paragraph block
        children = create_kwargs.kwargs["children"]
        assert len(children) == 1
        assert children[0]["type"] == "paragraph"

    @patch("monologue_tools.notion_push.Client")
    def test_publish_batches_over_100_blocks(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        page_id = "created-page-id"
        mock_client.pages.create.return_value = {
            "id": page_id,
            "url": "https://www.notion.so/test-page",
        }

        publisher = NotionPublisher(token="fake-token", parent_page_id="parent-id")
        # Create markdown with >100 paragraphs
        lines = [f"Paragraph {i}" for i in range(150)]
        md = "\n\n".join(lines)
        url = publisher.publish("Big Page", md)

        assert url == "https://www.notion.so/test-page"
        # First 100 blocks go with pages.create
        create_kwargs = mock_client.pages.create.call_args
        assert len(create_kwargs.kwargs["children"]) == 100
        # Remaining 50 blocks go via blocks.children.append
        mock_client.blocks.children.append.assert_called_once()
        append_kwargs = mock_client.blocks.children.append.call_args
        assert append_kwargs.kwargs["block_id"] == page_id
        assert len(append_kwargs.kwargs["children"]) == 50

    @patch("monologue_tools.notion_push.Client")
    def test_publish_batches_over_200_blocks(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        page_id = "created-page-id"
        mock_client.pages.create.return_value = {
            "id": page_id,
            "url": "https://www.notion.so/test-page",
        }

        publisher = NotionPublisher(token="fake-token", parent_page_id="parent-id")
        # Create markdown with 250 paragraphs
        lines = [f"Paragraph {i}" for i in range(250)]
        md = "\n\n".join(lines)
        publisher.publish("Huge Page", md)

        # First 100 with create, then 100+50 via two append calls
        assert mock_client.blocks.children.append.call_count == 2
        calls = mock_client.blocks.children.append.call_args_list
        assert len(calls[0].kwargs["children"]) == 100
        assert len(calls[1].kwargs["children"]) == 50

    @patch("monologue_tools.notion_push.Client")
    def test_update_replaces_content(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.blocks.children.list.return_value = {
            "results": [
                {"id": "block-1"},
                {"id": "block-2"},
            ]
        }

        publisher = NotionPublisher(token="fake-token", parent_page_id="parent-id")
        url = publisher.update(
            "https://www.notion.so/My-Page-abcdef12345678901234567890123456",
            "Updated Title",
            "New content here.",
        )

        # Title updated
        mock_client.pages.update.assert_called_once()
        # Old blocks deleted
        assert mock_client.blocks.delete.call_count == 2
        # New blocks appended
        mock_client.blocks.children.append.assert_called_once()

        assert url == "https://www.notion.so/My-Page-abcdef12345678901234567890123456"


class TestPageUrlToId:
    def test_standard_url(self):
        url = "https://www.notion.so/My-Page-abcdef12345678901234567890123456"
        page_id = page_url_to_id(url)
        assert page_id == "abcdef12-3456-7890-1234-567890123456"

    def test_url_with_query_params(self):
        url = "https://www.notion.so/My-Page-abcdef12345678901234567890123456?pvs=4"
        page_id = page_url_to_id(url)
        assert page_id == "abcdef12-3456-7890-1234-567890123456"

    def test_workspace_url(self):
        url = "https://notion.so/filecoin/abcdef12345678901234567890123456"
        page_id = page_url_to_id(url)
        assert page_id == "abcdef12-3456-7890-1234-567890123456"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            page_url_to_id("https://example.com/not-a-notion-page")
