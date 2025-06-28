import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Import the script without .py extension
import importlib.util

spec = importlib.util.spec_from_file_location(
    "notion_export_to_archive", "notion_export_to_archive"
)
notion_export_to_archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notion_export_to_archive)
filename_to_notion_id = notion_export_to_archive.filename_to_notion_id


class TestNotionExportToArchive(unittest.TestCase):
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
