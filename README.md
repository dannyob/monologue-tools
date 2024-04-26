# monologue-tools
Utilities for my work monologue (a stream of stuff that I am doing for others to ingest)

## Daily linkdumps

This [directory](./daily) covers the week-daily diary entries I aim to write.

### Canonicity and workflow

The files in [archive](./daily/archive) are the canonical daily entries. I
currently edit an entry on Notion, then I export that file into the
[inbox](./daily/inbox) directory using
[notion-export-to-archive](./scripts/notion-export-to-archive.py) script, which
also turns it into a (transformed) markdown file in that archive.

This markdown file is, in turn transformed into an email that gets inserted
into buttondown (an email newsletter handling service), and a version for
Slack.

### Installation

github clone dannyob/monologue-tools
cd monologue-tools
mkdir -p daily/archive
mkdir -p daily/inbox
pip install -r requirements.txt
npm -g install notion-exporter
. bin/m-activate
