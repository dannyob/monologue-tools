# monologue-tools
Utilities for my work monologue (a stream of stuff that I am doing for others to ingest)

## Daily linkdumps

This [directory](./daily) covers the week-daily diary entries I aim to write.

### Canonicity and workflow

The files in [archive](./daily/archive) are the canonical daily entries. I
currently edit an entry on Notion, then I export that file into the
[inbox](./daily/inbox) directory, where it is picked up by
[notion-export-to-archive](./scripts/notion-export-to-archive.py) script, and
turned into a (transformed) markdown file in that archive.

This markdown file is, in turn transformed into an email that gets inserted
into buttondown (an email newsletter handling service), and a version for
Slack.
