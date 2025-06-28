#!/usr/bin/env python
"""Inspect raw Notion page data to understand property structure."""

import os
import sys
import json
from notion.client import NotionClient

if "NOTION_TOKEN" not in os.environ:
    raise TypeError("Could not find NOTION_TOKEN environment variable")

client = NotionClient(token_v2=os.environ["NOTION_TOKEN"])


def inspect_page_structure(notion_url):
    """Deep dive into page structure to understand properties."""
    print(f"\nInspecting page: {notion_url}")
    print("=" * 80)
    
    page = client.get_block(notion_url)
    raw_data = page.get()
    
    # 1. Show basic page info
    print("\n1. Page Type and Basic Info:")
    print(f"   Type: {type(page).__name__}")
    print(f"   ID: {page.id}")
    print(f"   Title: {getattr(page, 'title', 'No title')}")
    
    # 2. Inspect properties structure
    if "properties" in raw_data:
        print("\n2. Properties Structure:")
        properties = raw_data["properties"]
        
        for key, value in properties.items():
            print(f"\n   Property key: '{key}'")
            print(f"   Raw key repr: {repr(key)}")  # Show exact representation
            print(f"   Value type: {type(value).__name__}")
            print(f"   Value structure: {json.dumps(value, indent=6)[:200]}...")
            
            # Try to extract URL-like values
            if isinstance(value, list) and len(value) > 0:
                try:
                    if isinstance(value[0], list) and len(value[0]) > 0:
                        first_val = value[0][0]
                        if isinstance(first_val, str):
                            print(f"   First value: {first_val}")
                            if first_val.startswith('http'):
                                print(f"   >>> URL FOUND: {first_val}")
                except:
                    pass
    
    # 3. Check for property schema or metadata
    print("\n3. Looking for property metadata:")
    for key in ['schema', 'collection', 'format', 'property_schema']:
        if key in raw_data:
            print(f"   Found '{key}': {json.dumps(raw_data[key], indent=6)[:200]}...")
    
    # 4. Parent information (might contain schema)
    if hasattr(page, 'parent'):
        print("\n4. Parent Information:")
        try:
            parent = page.parent
            print(f"   Parent type: {type(parent).__name__}")
            if hasattr(parent, 'collection'):
                print("   Parent has collection (database)")
                # Try to get schema
                try:
                    schema = parent.collection.get_schema()
                    print(f"   Schema found: {json.dumps(schema, indent=6)[:200]}...")
                except:
                    pass
        except:
            print("   Could not access parent")
    
    # 5. Full raw data (truncated for readability)
    print("\n5. Full Raw Data Structure (keys only):")
    for key in sorted(raw_data.keys()):
        print(f"   - {key}")
    
    return raw_data


if __name__ == "__main__":
    if len(sys.argv) > 1:
        notion_url = sys.argv[1]
        data = inspect_page_structure(notion_url)
        
        # Optionally save full data to file for analysis
        if len(sys.argv) > 2 and sys.argv[2] == "--save":
            with open("notion_page_data.json", "w") as f:
                json.dump(data, f, indent=2)
            print("\n\nFull data saved to notion_page_data.json")
    else:
        print("Usage: inspect_notion_page.py <notion_url> [--save]")
        print("\nThis script inspects the raw structure of a Notion page")
        print("to understand how properties are stored and accessed.")
        print("\nUse --save to dump full data to notion_page_data.json")