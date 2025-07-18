import datetime
import json
import os
import os.path
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from zipfile import ZipFile

import requests
from markdown import Markdown

from . import transformnotion


# ANSI color codes and formatting
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def hyperlink(url, text=None):
    """Create OSC 8 hyperlink"""
    if text is None:
        text = url
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_status(emoji, message, color=Colors.RESET):
    """Print formatted status message"""
    print(f"{color}{emoji} {message}{Colors.RESET}")


def print_info(message):
    print_status("ℹ️", message, Colors.CYAN)


def print_success(message):
    print_status("✅", message, Colors.GREEN)


def print_warning(message):
    print_status("⚠️", message, Colors.YELLOW)


def print_error(message):
    print_status("❌", message, Colors.RED)


def print_processing(message):
    print_status("⚙️", message, Colors.BLUE)


def clean_notion_url(url):
    """Strip URL fragments and query parameters from Notion URLs"""
    parsed = urlparse(url)
    # Remove query and fragment components
    cleaned = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return cleaned


BUTTONDOWN_API_KEY = os.getenv(
    "BUTTONDOWN_API_KEY", ""
)  # Get Buttondown API key from environment variable or default to empty string


def get_draft_emails_info():
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    }
    response = requests.get(
        "https://api.buttondown.email/v1/emails?status=draft", headers=headers
    )
    if response.status_code != 200:
        raise Exception(f"Failed to fetch emails: {response.status_code}")

    emails = response.json()["results"]
    draft_emails_info = {}
    for email in emails:
        if email["status"] == "draft":
            subject = email["subject"]
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", subject)
            if date_match:
                iso_date = date_match.group(0)
                draft_emails_info[iso_date] = email
    return draft_emails_info


def create_buttondown_draft(subject, body, mail_id=None):
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "subject": subject,
        "body": body,
        "status": "draft",
    }
    if mail_id:
        response = requests.patch(
            f"https://api.buttondown.email/v1/emails/{mail_id}",
            headers=headers,
            data=json.dumps(data),
        )
    else:
        response = requests.post(
            "https://api.buttondown.email/v1/emails",
            headers=headers,
            data=json.dumps(data),
        )

    buttondown_url = "https://buttondown.email/emails"
    print_info(f"Buttondown: {hyperlink(buttondown_url, 'buttondown.email/emails')}")

    if response.status_code == 201:
        print_success(f"Draft email created at Buttondown with subject: {subject}")
    elif response.status_code == 200:
        print_success(f"Draft email updated at Buttondown with subject: {subject}")
    elif response.headers.get("Content-Type", "").startswith("text/"):
        print_error(f"Failed to create draft email at Buttondown: {response.text}")
    else:
        print_error(
            f"Failed to create draft email at Buttondown: {response.status_code}"
        )


def export_notion_to_markdown(notion_url, inbox_path):
    notion_id = notion_url.rsplit("/", 1)[-1]
    output_filename = inbox_path / f"{notion_id}.md"
    with open(output_filename, "w") as output_file:
        process = subprocess.run(["notion-exporter", notion_url], stdout=output_file)
    if process.returncode != 0:
        raise Exception("Failed to export Notion page to markdown.")
    return output_filename


def find_first_line_with_hash(file_path):
    with open(file_path) as file:
        for line in file:
            if line.startswith("#"):
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                if date_match:
                    return line[
                        date_match.start() :
                    ].strip()  # Strip everything before the date
                else:
                    raise ValueError(
                        f"Subject line does not contain a valid date: {line}"
                    )
    return ""


def filename_to_notion_id(fname):
    match = re.search(r"([a-fA-F0-9]{32})", str(fname))
    if not match:
        raise TypeError(f"Could not find notion id in {fname}")
    return f"https://notion.so/filecoin/{match.group(1)}"


def main():
    """Main entry point for notion2monologue."""
    if not BUTTONDOWN_API_KEY:
        raise OSError("BUTTONDOWN_API_KEY environment variable not set.")

    current_file_path = Path(__file__).resolve().parent

    ROOT_DIR = current_file_path / ".." / ".."
    archive_path = ROOT_DIR / "daily/archive"
    inbox_path = ROOT_DIR / "daily/inbox"

    if len(sys.argv) > 1:
        notion_url = clean_notion_url(sys.argv[1])
        if notion_url.startswith("https://www.notion.so/filecoin/"):
            print_processing(f"Exporting Notion page: {hyperlink(notion_url)}")
            exported_file = export_notion_to_markdown(notion_url, inbox_path)
            print_success(f"Exported to {exported_file}")
        else:
            print_error("I only know how to export notion pages")
            sys.exit(1)

    if not archive_path.exists():
        raise FileNotFoundError(f"Could not find the specified file: {archive_path}")

    if not inbox_path.exists():
        raise FileNotFoundError(f"Could not find the specified file: {inbox_path}")

    md = Markdown(extensions=["meta"])

    required_metadata = ["notion-id", "last-modified", "subject"]

    archive_files_by_notion_id = {}

    for the_file in archive_path.glob("*.md"):
        with open(the_file) as file:
            md.convert(file.read())
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

        # Skip the rest of the processing if a Notion URL was provided
        if len(sys.argv) > 1 and clean_notion_url(sys.argv[1]).startswith(
            "https://www.notion.so/filecoin/"
        ):
            continue

    for the_file in inbox_path.glob("*.md"):
        notion_id = filename_to_notion_id(the_file)
        last_modified = datetime.datetime.isoformat(
            datetime.datetime.fromtimestamp(
                os.path.getmtime(the_file), datetime.timezone.utc
            )
        )
        subject = find_first_line_with_hash(the_file)
        if notion_id in archive_files_by_notion_id:
            if (
                last_modified
                <= archive_files_by_notion_id[notion_id]["last-modified"][0]
            ):
                continue
            os.remove(archive_files_by_notion_id[notion_id]["filename"])
        # Extract the date from the subject and format it correctly
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", subject)
        if date_match:
            formatted_date = date_match.group(0)
        else:
            raise ValueError(f"Subject line does not contain a valid date: {subject}")
        fname = formatted_date + ".md"
        with open(archive_path / fname, "w") as the_output_file:
            the_output_file.write(f"Notion-Id: {notion_id}\n")
            the_output_file.write(f"Last-Modified: {last_modified}\n")
            the_output_file.write(f"Subject: {subject}\n\n")
            with open(the_file) as the_input_file:
                while True:
                    the_line = the_input_file.readline()
                    if the_line.startswith("##"):  # Skip everything until a headline 2
                        break
                the_output_file.write(the_line)
                rendered_markdown, missing_links = transformnotion.transform_markdown(
                    the_input_file
                )
                the_output_file.write(rendered_markdown)

                # Handle missing links
                if missing_links:
                    print_warning(
                        f"Found {len(missing_links)} missing Notion links. Suggesting URLs..."
                    )
                    for (
                        link_text,
                        notion_url,
                        context,
                        page_title,
                        page_content,
                    ) in missing_links:
                        print_info(
                            f"Looking up URL for: {Colors.BOLD}{link_text}{Colors.RESET}"
                        )
                        try:
                            # Build prompt with all available context
                            prompt_parts = []

                            # Add linked page context if available
                            if page_title or page_content:
                                prompt_parts.append(
                                    f"The Notion page linked with '{link_text}' contains:"
                                )
                                if page_title:
                                    prompt_parts.append(f"- Title: {page_title}")
                                if page_content:
                                    # Limit page content to 200 chars
                                    truncated_content = (
                                        page_content[:200] + "..."
                                        if len(page_content) > 200
                                        else page_content
                                    )
                                    prompt_parts.append(
                                        f"- Content: {truncated_content}"
                                    )
                                prompt_parts.append("")

                            # Add paragraph context if available
                            if context and link_text in context:
                                # Extract a snippet around the link text
                                start_pos = max(0, context.find(link_text) - 150)
                                end_pos = min(
                                    len(context),
                                    context.find(link_text) + len(link_text) + 150,
                                )
                                snippet = context[start_pos:end_pos].strip()
                                if start_pos > 0:
                                    snippet = "..." + snippet
                                if end_pos < len(context):
                                    snippet = snippet + "..."
                                prompt_parts.append(
                                    f"The diary entry mentions '{link_text}' in this context: \"{snippet}\""
                                )
                                prompt_parts.append("")

                            # Build the main prompt
                            prompt = "\n".join(prompt_parts) if prompt_parts else ""
                            prompt += f"Find the canonical URL for '{link_text}'. "
                            prompt += f"Look for any URLs mentioned that relate to {link_text}. "
                            prompt += "If an exact URL is mentioned, return that. Otherwise, return the most likely canonical URL. "
                            prompt += "Output only the URL in markdown code blocks."

                            # Call llm -m sonar to get URL suggestion
                            llm_command = ["llm", "-m", "sonar", "-x", prompt]
                            result = subprocess.run(
                                llm_command, capture_output=True, text=True, timeout=30
                            )
                            if result.returncode == 0:
                                print_info(f"Suggested URL: {result.stdout.strip()}")
                                print_info(
                                    f"Original Notion URL: {hyperlink(notion_url)}"
                                )
                            else:
                                print_error(
                                    f"Failed to get URL suggestion: {result.stderr}"
                                )
                        except subprocess.TimeoutExpired:
                            print_error(
                                f"Timeout getting URL suggestion for: {link_text}"
                            )
                        except Exception as e:
                            print_error(f"Error getting URL suggestion: {e}")
                        print()  # Add spacing between suggestions
                else:
                    # No missing links, run grammar check
                    print_success(
                        "No missing Notion links found. Running grammar check..."
                    )
                    archive_file = archive_path / fname
                    try:
                        grammar_command = [
                            "llm",
                            "give me any typo or grammar fixes for this -- preferably as human readable diffs. "
                            "Highlight words to change, rather than whole chunks. Use markdown to express the changes",
                        ]
                        with open(archive_file) as f:
                            result = subprocess.run(
                                grammar_command,
                                input=f.read(),
                                capture_output=True,
                                text=True,
                                timeout=60,
                            )
                        if result.returncode == 0:
                            print_info("Grammar check results:")
                            print(result.stdout)
                        else:
                            print_error(f"Grammar check failed: {result.stderr}")
                    except subprocess.TimeoutExpired:
                        print_error("Grammar check timed out")
                    except Exception as e:
                        print_error(f"Error running grammar check: {e}")

                m = get_draft_emails_info()
                if formatted_date in m:
                    draft_id = m[formatted_date]["id"]
                    create_buttondown_draft(
                        subject, the_line + rendered_markdown, draft_id
                    )
                else:
                    create_buttondown_draft(subject, the_line + rendered_markdown)
        print_success(f"Written: {Colors.BOLD}{archive_path}/{fname}{Colors.RESET}")


if __name__ == "__main__":
    main()
