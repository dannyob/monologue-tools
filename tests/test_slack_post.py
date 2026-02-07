"""Tests for Slack posting."""

from unittest.mock import MagicMock, patch

import pytest

from monologue_tools.slack_post import SlackPublisher, markdown_to_mrkdwn


class TestMarkdownToMrkdwn:
    def test_bold(self):
        assert markdown_to_mrkdwn("**bold**") == "*bold*"

    def test_double_underscore_bold(self):
        assert markdown_to_mrkdwn("__bold__") == "*bold*"

    def test_italic_unchanged(self):
        assert markdown_to_mrkdwn("_italic_") == "_italic_"

    def test_links(self):
        assert (
            markdown_to_mrkdwn("[click](https://example.com)")
            == "<https://example.com|click>"
        )

    def test_h1_heading(self):
        assert markdown_to_mrkdwn("# Heading") == "*Heading*"

    def test_h2_heading(self):
        assert markdown_to_mrkdwn("## Sub Heading") == "*Sub Heading*"

    def test_h3_heading(self):
        assert markdown_to_mrkdwn("### Deep Heading") == "*Deep Heading*"

    def test_code_block_preserved(self):
        text = "```\ncode here\n```"
        assert markdown_to_mrkdwn(text) == text

    def test_bold_inside_code_block_not_converted(self):
        text = "```\n**not bold**\n```"
        assert markdown_to_mrkdwn(text) == text

    def test_horizontal_rule_unchanged(self):
        assert markdown_to_mrkdwn("---") == "---"

    def test_mixed_content(self):
        text = "# Title\n\n**bold** and _italic_ with [link](http://x.com)\n\n---"
        result = markdown_to_mrkdwn(text)
        assert (
            result == "*Title*\n\n*bold* and _italic_ with <http://x.com|link>\n\n---"
        )


class TestSlackPublisher:
    @patch("monologue_tools.slack_post.WebClient")
    def test_post_message_basic(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        result = pub.post_message(subject="2025-02-07: Test", body="Hello **world**")

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == "#monologue-danny"
        assert "*2025-02-07: Test*" in call_kwargs["text"]
        assert "*world*" in call_kwargs["text"]
        assert result == {"ok": True}

    @patch("monologue_tools.slack_post.WebClient")
    def test_post_message_with_notion_url(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        pub.post_message(
            subject="Test",
            body="body",
            notion_url="https://notion.so/page/123",
        )

        text = mock_client.chat_postMessage.call_args[1]["text"]
        assert "Notion: <https://notion.so/page/123>" in text

    @patch("monologue_tools.slack_post.WebClient")
    def test_post_message_with_buttondown_url(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        pub.post_message(
            subject="Test",
            body="body",
            buttondown_url="https://buttondown.com/archive/123",
        )

        text = mock_client.chat_postMessage.call_args[1]["text"]
        assert "Buttondown: <https://buttondown.com/archive/123>" in text

    @patch("monologue_tools.slack_post.WebClient")
    def test_post_message_with_both_urls(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        pub.post_message(
            subject="Test",
            body="body",
            notion_url="https://notion.so/page/123",
            buttondown_url="https://buttondown.com/archive/456",
        )

        text = mock_client.chat_postMessage.call_args[1]["text"]
        assert "Notion:" in text
        assert "Buttondown:" in text

    @patch("monologue_tools.slack_post.WebClient")
    def test_post_message_without_urls(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        pub.post_message(subject="Test", body="body")

        text = mock_client.chat_postMessage.call_args[1]["text"]
        assert "Notion:" not in text
        assert "Buttondown:" not in text

    @patch("monologue_tools.slack_post.WebClient")
    def test_create_canvas(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.canvases_create.return_value = {"ok": True, "canvas_id": "C123"}

        pub = SlackPublisher(token="xoxb-fake")
        result = pub.create_canvas(title="My Canvas", body="# Content")

        mock_client.canvases_create.assert_called_once_with(
            title="My Canvas",
            document_content={"type": "markdown", "markdown": "# Content"},
        )
        assert result["canvas_id"] == "C123"

    @patch("monologue_tools.slack_post.WebClient")
    def test_post_canvas(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "channels": [{"name": "monologue-danny", "id": "C999"}],
            "response_metadata": {"next_cursor": ""},
        }
        mock_client.conversations_canvases_create.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        result = pub.post_canvas(title="Title", body="Body")

        mock_client.conversations_canvases_create.assert_called_once_with(
            channel_id="C999",
            document_content={"type": "markdown", "markdown": "Body"},
            title="Title",
        )
        assert result == {"ok": True}

    @patch("monologue_tools.slack_post.WebClient")
    def test_resolve_channel_id_not_found(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "channels": [],
            "response_metadata": {"next_cursor": ""},
        }

        pub = SlackPublisher(token="xoxb-fake")
        with pytest.raises(ValueError, match="Channel not found"):
            pub._resolve_channel_id()

    @patch("monologue_tools.slack_post.WebClient")
    def test_custom_channel(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake", channel="#other-channel")
        pub.post_message(subject="Test", body="body")

        assert mock_client.chat_postMessage.call_args[1]["channel"] == "#other-channel"

    @patch("monologue_tools.slack_post.WebClient")
    def test_update_message(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_update.return_value = {"ok": True, "ts": "123.456"}

        pub = SlackPublisher(token="xoxb-fake")
        pub.update_message(ts="123.456", subject="Updated", body="New **body**")

        mock_client.chat_update.assert_called_once()
        call_kwargs = mock_client.chat_update.call_args[1]
        assert call_kwargs["channel"] == "#monologue-danny"
        assert call_kwargs["ts"] == "123.456"
        assert "*Updated*" in call_kwargs["text"]
        assert "*body*" in call_kwargs["text"]

    @patch("monologue_tools.slack_post.WebClient")
    def test_update_message_with_urls(self, MockWebClient):
        mock_client = MagicMock()
        MockWebClient.return_value = mock_client
        mock_client.chat_update.return_value = {"ok": True}

        pub = SlackPublisher(token="xoxb-fake")
        pub.update_message(
            ts="123.456",
            subject="Test",
            body="body",
            notion_url="https://notion.so/page",
        )

        text = mock_client.chat_update.call_args[1]["text"]
        assert "Notion: <https://notion.so/page>" in text
