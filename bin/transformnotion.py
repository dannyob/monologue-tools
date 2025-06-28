#!/usr/bin/env python
import os
from marko import Markdown
from marko.md_renderer import MarkdownRenderer
from marko import inline
from notion.client import NotionClient

if "NOTION_TOKEN" not in os.environ:
    raise TypeError("Could not find NOTION_TOKEN environment variable")
client = NotionClient(token_v2=os.environ["NOTION_TOKEN"])


def get_redirected_url(notion_url):
    page = client.get_block(notion_url)
    alternative_url = None
    try:
        # magic notion goo
        alternative_url = page.get()["properties"]["n\\G@"][0][0]
    except (KeyError, IndexError):
        return notion_url
    if alternative_url:
        return alternative_url
    return notion_url


class URLRewritingMarkdownRenderer(MarkdownRenderer):
    def __init__(self):
        super().__init__()
        self.missing_links = []
    def render_link(self, element: inline.Link) -> str:
        link_text = self.render_children(element)
        link_title = (
            '"{}"'.format(element.title.replace('"', '\\"')) if element.title else None
        )
        assert self.root_node
        label = next(
            (
                k
                for k, v in self.root_node.link_ref_defs.items()
                if v == (element.dest, link_title)
            ),
            None,
        )
        if label is not None:
            if label == link_text:
                return f"[{label}]"
            return f"[{link_text}][{label}]"
        title = f" {link_title}" if link_title is not None else ""
        if not element.dest.startswith("https://www.notion.so/"):
            return f"[{link_text}]({element.dest}{title})"
        link_dest = get_redirected_url(element.dest)
        if link_dest == element.dest:
            self.missing_links.append((link_text, element.dest))
            print(f"⚠️  \033[33mWarning: No redirection found for {element.dest}\033[0m")
        if link_dest == element.dest:
            return f"[{link_text}]({element.dest}{title})"
        return f"[{link_text}]({link_dest}{title}) [🄽]({element.dest})"


def transform_markdown(file):
    parsed_markdown = Markdown().parse(file.read())
    transforming_renderer = URLRewritingMarkdownRenderer()
    rendered_content = transforming_renderer.render(parsed_markdown)
    return rendered_content, transforming_renderer.missing_links
