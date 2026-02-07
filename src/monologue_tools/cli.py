"""Monologue CLI - publish daily writing to multiple platforms."""

import os
from pathlib import Path

import click

from .markdown_utils import parse_markdown_file
from .output import hyperlink, print_error, print_info, print_processing, print_success


@click.group()
@click.version_option()
def cli():
    """Monologue: publish your daily writing to multiple platforms."""


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--to",
    "targets",
    multiple=True,
    type=click.Choice(["notion", "buttondown", "slack"]),
    help="Publish to specific targets (default: all)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be published without doing it"
)
@click.option(
    "--canvas", is_flag=True, help="Post to Slack as a Canvas instead of a message"
)
def publish(file: Path, targets: tuple, dry_run: bool, canvas: bool):
    """Publish a markdown file to configured platforms.

    Reads a markdown file and pushes it to Notion, Buttondown, and/or Slack.
    The file can be plain markdown (with an H1 containing the date and title)
    or an archive-format file with metadata headers.
    """
    if not targets:
        targets = ("notion", "buttondown", "slack")

    entry = parse_markdown_file(file)
    print_processing(f"Publishing: {entry.subject}")

    if dry_run:
        print_info(f"Title: {entry.title}")
        print_info(f"Date: {entry.date_str}")
        print_info(f"Subject: {entry.subject}")
        print_info(f"Body: {len(entry.body)} characters")
        print_info(f"Targets: {', '.join(targets)}")
        return

    results = {}

    if "notion" in targets:
        results["notion"] = _publish_notion(entry)

    if "buttondown" in targets:
        results["buttondown"] = _publish_buttondown(entry)

    if "slack" in targets:
        results["slack"] = _publish_slack(
            entry, canvas=canvas, notion_url=results.get("notion")
        )

    published = [t for t in targets if results.get(t)]
    if published:
        print_success(f"Published to: {', '.join(published)}")
    else:
        print_error("Nothing was published (check environment variables)")


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def info(file: Path):
    """Show parsed metadata for a markdown file."""
    entry = parse_markdown_file(file)
    click.echo(f"Title:   {entry.title}")
    click.echo(f"Date:    {entry.date_str}")
    click.echo(f"Subject: {entry.subject}")
    if entry.notion_id:
        click.echo(f"Notion:  {entry.notion_id}")
    click.echo(f"Body:    {len(entry.body)} characters")


def _publish_notion(entry) -> str | None:
    """Publish to Notion. Returns the page URL."""
    token = os.environ.get("NOTION_TOKEN")
    parent = os.environ.get("NOTION_PARENT_PAGE_ID")
    if not token:
        print_error("NOTION_TOKEN not set, skipping Notion")
        return None
    if not parent:
        print_error("NOTION_PARENT_PAGE_ID not set, skipping Notion")
        return None

    from .notion_push import NotionPublisher

    publisher = NotionPublisher(token, parent)
    url = publisher.publish(entry.subject, entry.body)
    print_success(f"Notion: {hyperlink(url)}")
    return url


def _publish_buttondown(entry) -> str | None:
    """Publish to Buttondown. Returns the email ID."""
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print_error("BUTTONDOWN_API_KEY not set, skipping Buttondown")
        return None

    from .buttondown import ButtondownClient

    client = ButtondownClient(api_key)
    result = client.publish(entry.subject, entry.body)
    buttondown_url = "https://buttondown.email/emails"
    print_success(f"Buttondown: {hyperlink(buttondown_url, 'draft created')}")
    return result.get("id")


def _publish_slack(entry, canvas=False, notion_url=None) -> str | None:
    """Publish to Slack. Returns message timestamp or canvas ID."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL", "#monologue-danny")
    if not token:
        print_error("SLACK_BOT_TOKEN not set, skipping Slack")
        return None

    from .slack_post import SlackPublisher

    publisher = SlackPublisher(token, channel)

    if canvas:
        result = publisher.post_canvas(entry.subject, entry.body)
        print_success(f"Slack: canvas created in {channel}")
        return result.get("canvas_id")
    else:
        result = publisher.post_message(
            entry.subject,
            entry.body,
            notion_url=notion_url,
        )
        print_success(f"Slack: posted to {channel}")
        return result.get("ts")
