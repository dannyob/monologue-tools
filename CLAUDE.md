# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal monologue tools repository for managing daily diary entries and email newsletters. The workflow involves:

1. Writing entries in Notion
2. Exporting from Notion to local markdown files
3. Processing markdown for different output formats (email, Slack)
4. Publishing to Buttondown email service

## Environment Setup

The project uses a Python virtual environment with encrypted environment variables:

```bash
# Initial setup
python -m venv .venv --prompt mono
pip install -r requirements.txt
npm -g install notion-exporter

# Activate environment (source this file)
. bin/m-activate
```

The `bin/m-activate` script:
- Activates the Python virtual environment
- Adds `bin/` to PATH
- Loads encrypted environment variables from `~/Private/secrets/monologue/env.gpg`
- Sets up project-specific shell utilities

## Key Scripts and Commands

### Main Processing Script
- `bin/notion2monologue` - Main Python script that:
  - Exports Notion pages to markdown using `notion-exporter`
  - Processes markdown files from `daily/inbox/` to `daily/archive/`
  - Creates/updates Buttondown email drafts via API
  - Handles file metadata and date parsing

### Supporting Scripts
- `bin/transformnotion.py` - Markdown transformer that rewrites Notion URLs
- `bin/copy_markdown_with_preamble.sh` - Formats content for Slack with preambles
- `bin/test_notion2monologue.py` - Unit tests for the main script

### Running Tests
```bash
python bin/test_notion2monologue.py
```

### Code Quality
```bash
# Pre-commit hooks with ruff are configured
# Run linting manually:
ruff check .
ruff format .
```

## Directory Structure

- `daily/archive/` - Canonical daily entries (YYYY-MM-DD.md format)
- `daily/inbox/` - Temporary storage for Notion exports before processing
- `bin/` - Executable scripts and utilities

## Key Environment Variables

Required environment variables (stored in encrypted file):
- `BUTTONDOWN_API_KEY` - For Buttondown email service API
- `NOTION_TOKEN` - For Notion API access

Note: Environment variables are encrypted with GPG and automatically loaded by `bin/m-activate`

## File Formats

### Archive Files
Each file in `daily/archive/` has metadata headers:
```
Notion-Id: https://notion.so/filecoin/[32-char-hex-id]
Last-Modified: [ISO datetime]
Subject: [YYYY-MM-DD subject line]

## [Content starts here]
```

### Workflow
1. Export from Notion using the main script with a Notion URL
2. Script processes inbox files and moves them to archive
3. Creates/updates Buttondown email drafts automatically
4. Use `copy_markdown_with_preamble.sh` to format for Slack posting

## Dependencies

Key Python packages:
- `markdown` - Markdown processing
- `requests` - HTTP API calls
- `marko` - Advanced markdown parsing
- `notion-py` - Notion API integration
- `beautifulsoup4` - HTML/XML parsing

The project also uses `notion-exporter` (npm package) for Notion page exports.

## Architecture Notes

- Mixed tech stack: Python (main processing) + Node.js (notion-exporter) + shell scripts
- Pipeline: Notion → inbox → archive → email/Slack formatting
- File processing preserves metadata headers for tracking and automation
- Custom activation script provides project-specific environment and utilities