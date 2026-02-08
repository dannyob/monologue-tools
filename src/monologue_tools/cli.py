"""Monologue CLI - publish daily writing to multiple platforms."""

import os
from pathlib import Path

import click

from .markdown_utils import parse_markdown_file, write_metadata
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
@click.option(
    "--draft",
    is_flag=True,
    help="Draft only: publish to Buttondown (as draft), skip Notion and Slack",
)
def publish(file: Path, targets: tuple, dry_run: bool, canvas: bool, draft: bool):
    """Publish a markdown file to configured platforms.

    Reads a markdown file and pushes it to Notion, Buttondown, and/or Slack.
    On first publish, creates new entries. On re-publish, updates existing
    entries using IDs stored in the file's metadata headers.
    """
    if draft:
        targets = ("buttondown",)
    elif not targets:
        targets = ("notion", "buttondown", "slack")

    entry = parse_markdown_file(file)
    meta = entry.metadata
    print_processing(f"Publishing: {entry.subject}")

    if dry_run:
        print_info(f"Title: {entry.title}")
        print_info(f"Date: {entry.date_str}")
        print_info(f"Subject: {entry.subject}")
        print_info(f"Body: {len(entry.body)} characters")
        print_info(f"Targets: {', '.join(targets)}")
        for key in ("notion_id", "buttondown_id", "slack_ts"):
            if key in meta:
                print_info(f"Existing {key}: {meta[key]} (will update)")
        return

    results = {}
    metadata_updates = {}

    if "notion" in targets:
        url = _publish_notion(entry)
        results["notion"] = url
        if url:
            metadata_updates["notion_id"] = url

    if "buttondown" in targets:
        email_id = _publish_buttondown(entry)
        results["buttondown"] = email_id
        if email_id:
            metadata_updates["buttondown_id"] = email_id

    if "slack" in targets:
        slack_result = _publish_slack(
            entry, canvas=canvas, notion_url=results.get("notion")
        )
        results["slack"] = slack_result
        if slack_result:
            metadata_updates["slack_ts"] = slack_result
            channel = os.environ.get("SLACK_CHANNEL", "#monologue-danny")
            metadata_updates["slack_channel"] = channel

    # Write metadata back to the source file for idempotent re-publishing
    if metadata_updates:
        write_metadata(file, metadata_updates)
        print_info(f"Metadata saved to {file}")

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
    for key in ("buttondown_id", "slack_ts", "slack_channel"):
        if key in entry.metadata:
            click.echo(f"{key}: {entry.metadata[key]}")
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

    existing_url = entry.metadata.get("notion_id")
    if existing_url:
        url = publisher.update(existing_url, entry.subject, entry.body)
        print_success(f"Notion: updated {hyperlink(url)}")
    else:
        url = publisher.publish(entry.subject, entry.body)
        print_success(f"Notion: created {hyperlink(url)}")
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
    print_success(f"Buttondown: {hyperlink(buttondown_url, 'draft created/updated')}")
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

    existing_ts = entry.metadata.get("slack_ts")
    if existing_ts:
        result = publisher.update_message(
            existing_ts,
            entry.subject,
            entry.body,
            notion_url=notion_url,
        )
        print_success(f"Slack: updated in {channel}")
    else:
        result = publisher.post_message(
            entry.subject,
            entry.body,
            notion_url=notion_url,
        )
        print_success(f"Slack: posted to {channel}")
    return result.get("ts")
