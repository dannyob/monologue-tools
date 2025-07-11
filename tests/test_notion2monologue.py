import os
import sys
import unittest

# Add the src directory to the path
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from monologue_tools.notion2monologue import filename_to_notion_id


class TestNotion2Monologue(unittest.TestCase):
    def test_filename_to_notion_id(self):
        # Test with a valid filename containing a Notion ID
        filename = "20210401-This-is-a-test-abcdef123456abcdef123456abcdef12.md"
        expected_notion_id = (
            "https://notion.so/filecoin/abcdef123456abcdef123456abcdef12"
        )
        self.assertEqual(filename_to_notion_id(filename), expected_notion_id)

        # Test with a filename that does not contain a Notion ID
        filename = "20210401-This-is-a-test-with-no-id.md"
        with self.assertRaises(TypeError):
            filename_to_notion_id(filename)


if __name__ == "__main__":
    unittest.main()
