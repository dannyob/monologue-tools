#!/usr/bin/env python
import os
from marko import Markdown
from marko.md_renderer import MarkdownRenderer
from marko import inline, block
from notion.client import NotionClient

if "NOTION_TOKEN" not in os.environ:
    raise TypeError("Could not find NOTION_TOKEN environment variable")
client = NotionClient(token_v2=os.environ["NOTION_TOKEN"])


def get_redirected_url_and_content(notion_url):
    """Get redirect URL and page content for context."""
    page = client.get_block(notion_url)
    alternative_url = None
    page_title = ""
    page_content = ""
    
    try:
        # magic notion goo - check for redirect URL
        alternative_url = page.get()["properties"]["n\\G@"][0][0]
    except (KeyError, IndexError):
        # No redirect found - get page content for context
        try:
            # Get page title
            page_title = getattr(page, 'title', '')
            
            # Extract first few paragraphs of content
            content_parts = []
            child_count = 0
            max_children = 5  # Limit to first 5 blocks
            
            for child in page.children:
                if child_count >= max_children:
                    break
                
                # Skip certain block types
                if hasattr(child, 'type') and child.type in ['divider', 'table_of_contents']:
                    continue
                
                # Extract text content
                if hasattr(child, 'title'):
                    text = str(child.title).strip()
                    if text:
                        content_parts.append(text)
                        child_count += 1
            
            page_content = ' '.join(content_parts[:3])  # Use first 3 paragraphs
            
        except Exception as e:
            print(f"    Could not fetch page content: {e}")
    
    return alternative_url or notion_url, page_title, page_content


class URLRewritingMarkdownRenderer(MarkdownRenderer):
    def __init__(self):
        super().__init__()
        self.missing_links = []
        self.content_chunks = []
        self.current_paragraph = None
        self.current_list_item = None

    def render_paragraph(self, element) -> str:
        # Store reference to current paragraph element
        self.current_paragraph = element
        # Render the paragraph content
        paragraph_content = self.render_children(element)
        # Clear current paragraph reference
        self.current_paragraph = None
        return paragraph_content + "\n\n"
    
    def render_list_item(self, element) -> str:
        # Store reference to current list item element
        self.current_list_item = element
        # Render the list item content
        list_item_content = super().render_list_item(element)
        # Clear current list item reference
        self.current_list_item = None
        return list_item_content

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
        link_dest, page_title, page_content = get_redirected_url_and_content(element.dest)
        if link_dest == element.dest:
            # Store the missing link with context
            context_element = self.current_paragraph or self.current_list_item
            self.missing_links.append((link_text, element.dest, context_element, page_title, page_content))
            print(f"⚠️  \033[33mWarning: No redirection found for {element.dest}\033[0m")
        if link_dest == element.dest:
            return f"[{link_text}]({element.dest}{title})"
        return f"[{link_text}]({link_dest}{title}) [🄽]({element.dest})"


def extract_paragraph_text(element):
    """Extract plain text from a paragraph or list item element for context."""
    if not element:
        return ""
    
    text_parts = []
    
    def extract_text(elem):
        # Handle different element types
        elem_type = type(elem).__name__
        
        if elem_type == 'RawText':
            # RawText stores content in 'children' attribute as a string
            if hasattr(elem, 'children') and isinstance(elem.children, str):
                text_parts.append(elem.children)
        elif elem_type == 'Link':
            # For links, extract the link text
            if hasattr(elem, 'children'):
                for child in elem.children:
                    extract_text(child)
        elif hasattr(elem, 'children') and hasattr(elem.children, '__iter__'):
            # Recursively process children
            for child in elem.children:
                extract_text(child)
        elif hasattr(elem, 'content'):
            text_parts.append(str(elem.content))
    
    extract_text(element)
    return ' '.join(text_parts)


def transform_markdown(file):
    content = file.read()
    parsed_markdown = Markdown().parse(content)
    transforming_renderer = URLRewritingMarkdownRenderer()
    rendered_content = transforming_renderer.render(parsed_markdown)
    
    # Process missing links to extract paragraph context
    processed_missing_links = []
    for link_text, notion_url, paragraph_element, page_title, page_content in transforming_renderer.missing_links:
        context = extract_paragraph_text(paragraph_element)
        processed_missing_links.append((link_text, notion_url, context, page_title, page_content))
    
    return rendered_content, processed_missing_links