"""Tests for the monologue CLI."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from monologue_tools.cli import cli


@pytest.fixture
def runner():
    """CliRunner that mixes stderr into output for easy assertion."""
    return CliRunner()


@pytest.fixture
def sample_markdown(tmp_path):
    md_file = tmp_path / "2025-02-07-test.md"
    md_file.write_text(
        "# 2025-02-07: Test Post\n\n## Working on\n\nSomething interesting.\n"
    )
    return md_file


@pytest.fixture
def archive_markdown(tmp_path):
    md_file = tmp_path / "2024-04-23.md"
    md_file.write_text(
        "---\n"
        "title: Numbers, TechSoup, Krazam\n"
        "date: 2024-04-23\n"
        "notion_id: https://notion.so/filecoin/abc123\n"
        "---\n\n"
        "## Three Things I Did\n\nSome content.\n"
    )
    return md_file


class TestPublishDryRun:
    def test_dry_run_shows_info(self, runner, sample_markdown):
        result = runner.invoke(cli, ["publish", str(sample_markdown), "--dry-run"])
        assert result.exit_code == 0
        assert "Test Post" in result.output
        assert "2025-02-07" in result.output

    def test_dry_run_with_archive_format(self, runner, archive_markdown):
        result = runner.invoke(cli, ["publish", str(archive_markdown), "--dry-run"])
        assert result.exit_code == 0
        assert "Numbers, TechSoup, Krazam" in result.output

    def test_dry_run_specific_target(self, runner, sample_markdown):
        result = runner.invoke(
            cli,
            ["publish", str(sample_markdown), "--dry-run", "--to", "buttondown"],
        )
        assert result.exit_code == 0
        assert "buttondown" in result.output


class TestPublishDraft:
    def test_draft_only_targets_buttondown(self, runner, sample_markdown):
        """--draft should only attempt Buttondown, skipping Notion and Slack."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "NOTION_TOKEN",
                "NOTION_PARENT_PAGE_ID",
                "BUTTONDOWN_API_KEY",
                "SLACK_BOT_TOKEN",
            )
        }
        result = runner.invoke(
            cli, ["publish", str(sample_markdown), "--draft"], env=env
        )
        assert result.exit_code == 0
        assert "BUTTONDOWN_API_KEY not set" in result.output
        # Should NOT mention Notion or Slack at all
        assert "NOTION" not in result.output
        assert "SLACK" not in result.output

    def test_draft_dry_run_shows_only_buttondown(self, runner, sample_markdown):
        result = runner.invoke(
            cli, ["publish", str(sample_markdown), "--draft", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "buttondown" in result.output
        assert "notion" not in result.output.lower().split("notion_id")[0]


class TestPublishNoCredentials:
    def test_publish_without_env_vars(self, runner, sample_markdown):
        """Without env vars, all targets should be skipped gracefully."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "NOTION_TOKEN",
                "NOTION_PARENT_PAGE_ID",
                "BUTTONDOWN_API_KEY",
                "SLACK_BOT_TOKEN",
            )
        }
        result = runner.invoke(cli, ["publish", str(sample_markdown)], env=env)
        assert result.exit_code == 0
        assert "not set" in result.output


class TestInfoCommand:
    def test_info_plain_markdown(self, runner, sample_markdown):
        result = runner.invoke(cli, ["info", str(sample_markdown)])
        assert result.exit_code == 0
        assert "Test Post" in result.output
        assert "2025-02-07" in result.output

    def test_info_archive_format(self, runner, archive_markdown):
        result = runner.invoke(cli, ["info", str(archive_markdown)])
        assert result.exit_code == 0
        assert "Numbers, TechSoup, Krazam" in result.output
        assert "notion.so" in result.output


class TestPublishTargets:
    def test_invalid_target(self, runner, sample_markdown):
        result = runner.invoke(
            cli, ["publish", str(sample_markdown), "--to", "invalid"]
        )
        assert result.exit_code != 0

    def test_nonexistent_file(self, runner):
        result = runner.invoke(cli, ["publish", "/nonexistent/file.md"])
        assert result.exit_code != 0
