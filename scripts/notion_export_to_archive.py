#!/usr/bin/env python

import datetime
import os
import os.path
import re
from pathlib import Path
import markdown
import requests
import json
from zipfile import ZipFile
import transformnotion

def create_buttondown_draft(subject, body):
def create_buttondown_draft(subject, body, metadata):
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "subject": subject,
        "body": body,
        "status": "draft",
        "metadata": metadata,
    }
    response = requests.post(
        "https://api.buttondown.email/v1/emails",
        headers=headers,
        data=json.dumps(data)
    )
    if response.status_code == 201:
        print(f"Draft email created at Buttondown with subject: {subject}")
    else:
        print(f"Failed to create draft email at Buttondown: {response.content}")
    print(f"Written: {fname}")


BUTTONDOWN_API_KEY = os.getenv('BUTTONDOWN_API_KEY')  # Get Buttondown API key from environment variable

current_file_path = Path(__file__).resolve().parent

ROOT_DIR = current_file_path / ".."
archive_path = ROOT_DIR / "daily/archive"
inbox_path = ROOT_DIR / "daily/inbox"

if not archive_path.exists():
    raise FileNotFoundError(f"Could not find the specified file: {archive_path}")

if not inbox_path.exists():
    raise FileNotFoundError(f"Could not find the specified file: {inbox_path}")

md = markdown.Markdown(extensions=["meta"])

required_metadata = ["notion-id", "last-modified", "subject"]

archive_files_by_notion_id = {}

for the_file in archive_path.glob("*.md"):
    markdown = md.convert(open(the_file).read())
    metadata = md.Meta
    if not all(elem in metadata.keys() for elem in required_metadata):
        raise Exception(f"{the_file} does not have all the metadata")
    archive_files_by_notion_id[metadata["notion-id"][0]] = {
        "filename": the_file,
        **metadata,
    }

for the_file in inbox_path.glob("*.zip"):
    with ZipFile(the_file, "r") as zip_file:
        zip_file.extractall(inbox_path)
    os.remove(the_file)


def find_first_line_with_hash(file_path):
    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("#"):
                return line.strip()[1:]  # Remove leading/trailing whitespace
    return ""


def filename_to_notion_id(fname):
    match = re.search(r"([a-fA-F0-9]{32})", str(fname))
    if not match:
        raise TypeError(f"Could not find notion id in {fname}")
    return f"https://notion.so/filecoin/{match.group(1)}"


for the_file in inbox_path.glob("*.md"):
    notion_id = filename_to_notion_id(the_file)
    last_modified = datetime.datetime.isoformat(
        datetime.datetime.fromtimestamp(
            os.path.getmtime(the_file), datetime.timezone.utc
        )
    )
    subject = find_first_line_with_hash(the_file)
    if notion_id in archive_files_by_notion_id:
        if last_modified <= archive_files_by_notion_id[notion_id]["last-modified"][0]:
            print(f"Newer archived {notion_id} found, skipping.")
            continue
        os.remove(archive_files_by_notion_id[notion_id]["filename"])
    fname = subject[1:11] + ".md"
    with open(archive_path / fname, "w") as the_output_file:
        the_output_file.write(f"Notion-Id: {notion_id}\n")
        the_output_file.write(f"Last-Modified: {last_modified}\n")
        the_output_file.write(f"Subject: {subject}\n\n")
        with open(the_file, "r") as the_input_file:
            while True:
                the_line = the_input_file.readline()
                if the_line.startswith("##"):  # Skip everything until a headline 2
                    break
            the_output_file.write(the_line)
            rendered_markdown = transformnotion.transform_markdown(the_input_file)
            the_output_file.write(rendered_markdown)
            metadata = {
                "notion_id": notion_id,
                "last_modified": last_modified
            }
            create_buttondown_draft(subject, the_line + rendered_markdown, metadata)
    print(f"Written: {fname}")


#
# for each zipfile in the inbox
# collect their contents and last modified
# replace any in our list and just keep the most recent
# deduce the original notion name
# is there already a mapping
#       say whether it is older or newer than the current file
#  do we have a -f flag?
#   no?
#     tell 'em to come back with an -f flag;
#     exit
#   yes?
#      say omg we're going to overwrite
#
# run the markdown through our list of filters, which should include
#  adding the metadata to the top
#  putting any images or external stuff onto filecoin/ipfs and changing the
#  href to point to this munging our Notion links so that they are marked with
#  a little unicode N copy it over to the archive
