"""Post monologue content to Slack."""

import re

from slack_sdk import WebClient


class SlackPublisher:
    def __init__(self, token: str, channel: str = "#monologue-danny"):
        self.client = WebClient(token=token)
        self.channel = channel

    def post_message(
        self,
        subject: str,
        body: str,
        notion_url: str | None = None,
        buttondown_url: str | None = None,
    ) -> dict:
        preamble = f"*{subject}*\n"
        if notion_url:
            preamble += f"Notion: <{notion_url}>\n"
        if buttondown_url:
            preamble += f"Buttondown: <{buttondown_url}>\n"
        preamble += "\n"
        text = preamble + markdown_to_mrkdwn(body)
        return self.client.chat_postMessage(channel=self.channel, text=text)

    def create_canvas(self, title: str, body: str) -> dict:
        return self.client.canvases_create(
            title=title,
            document_content={"type": "markdown", "markdown": body},
        )

    def post_canvas(self, title: str, body: str) -> dict:
        channel_id = self._resolve_channel_id()
        return self.client.conversations_canvases_create(
            channel_id=channel_id,
            document_content={"type": "markdown", "markdown": body},
            title=title,
        )

    def _resolve_channel_id(self) -> str:
        name = self.channel.lstrip("#")
        cursor = None
        while True:
            kwargs = {"limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            resp = self.client.conversations_list(**kwargs)
            for ch in resp["channels"]:
                if ch["name"] == name:
                    return ch["id"]
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        raise ValueError(f"Channel not found: {self.channel}")


def markdown_to_mrkdwn(text: str) -> str:
    """Convert standard markdown to Slack mrkdwn format."""
    lines = text.split("\n")
    result = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Headings → bold
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            result.append(f"*{heading_match.group(2)}*")
            continue

        # Links: [text](url) → <url|text>
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", line)

        # Bold: **text** → *text*
        # Handle both **text** and __text__
        line = re.sub(r"\*\*(.+?)\*\*", r"*\1*", line)
        line = re.sub(r"__(.+?)__", r"*\1*", line)

        result.append(line)

    return "\n".join(result)
