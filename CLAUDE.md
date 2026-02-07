# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CLI tool for publishing daily monologue entries to multiple platforms. The workflow:

1. Write a markdown file locally (with `# YYYY-MM-DD: Title` heading)
2. Run `monologue publish <file.md>` to push to Notion, Buttondown, and Slack

## Environment Setup

```bash
python -m venv .venv --prompt mono
pip install -e ".[dev,test]"

# Activate environment (loads encrypted secrets)
. bin/m-activate
```

The `bin/m-activate` script activates the venv and loads encrypted environment variables from `~/Private/secrets/monologue/env.gpg`.

## CLI Usage

```bash
# Publish to all platforms
monologue publish daily/2025-02-07.md

# Publish to specific targets
monologue publish post.md --to buttondown --to slack

# Dry run (show what would be published)
monologue publish post.md --dry-run

# Post to Slack as a Canvas instead of a message
monologue publish post.md --to slack --canvas

# Show parsed metadata
monologue info post.md
```

## Running Tests

```bash
pytest                  # run all tests
pytest -v               # verbose output
pytest tests/test_cli.py  # specific test file
```

## Code Quality

```bash
ruff check .
ruff format .
```

## Project Structure

```
src/monologue_tools/
  cli.py             - Click CLI (entry point: `monologue`)
  buttondown.py      - Buttondown email API client
  notion_push.py     - Push markdown to Notion pages
  slack_post.py      - Post to Slack (messages or canvases)
  markdown_utils.py  - Parse monologue markdown files
  output.py          - Terminal output utilities
tests/
  test_cli.py
  test_buttondown.py
  test_notion_push.py
  test_slack_post.py
  test_markdown_utils.py
daily/archive/         - Published entries (YYYY-MM-DD.md)
bin/                   - Legacy scripts and m-activate
```

## Environment Variables

Required (loaded by `bin/m-activate`):
- `BUTTONDOWN_API_KEY` - Buttondown email service API key
- `NOTION_TOKEN` - Notion integration token
- `NOTION_PARENT_PAGE_ID` - Notion page ID where new pages are created
- `SLACK_BOT_TOKEN` - Slack bot token (xoxb-...)
- `SLACK_CHANNEL` - Slack channel (default: `#monologue-danny`)

Each target is skipped gracefully if its env vars aren't set.

## Input Formats

### Plain markdown (preferred)
```markdown
# 2025-02-07: My Post Title

## Working on
Content here...
```

### Archive format (backward compatible)
```
Notion-Id: https://notion.so/filecoin/[hex-id]
Subject: 2025-02-07: My Post Title

## Working on
Content here...
```

## Dependencies

- `click` - CLI framework
- `requests` - Buttondown API
- `notion-client` - Official Notion SDK
- `slack-sdk` - Official Slack SDK

## Architecture Notes

- Single CLI entry point (`monologue`) with Click
- Each publishing target is an independent module with its own client class
- Markdown parsing supports both plain files and the legacy archive format
- All API interactions use proper SDK clients, no shell subprocess calls
- 70 tests covering all modules
