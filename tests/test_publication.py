import copy
import tempfile
import unittest
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from publication import ROOT, build_html, read_book


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("book", "standards", "docs"):
            shutil.copytree(ROOT / directory, self.root / directory)

    def test_reader_output_omits_metadata_and_follows_manifest(self):
        manifest, documents = read_book(self.root)
        output = build_html(manifest, documents)
        self.assertNotIn("original sources retained under chapters/", output)
        self.assertNotIn("meta:", output)
        self.assertLess(output.index('id="context-and-identity"'), output.index('id="intelligence"'))
        self.assertLess(output.index('id="response"'), output.index('id="automation"'))
        self.assertIn("reference--architecture", output)

    def test_unresolved_cross_reference_fails_build(self):
        p = self.root / "book/chapters/context-and-identity.yaml"
        p.write_text(p.read_text().replace("intelligence#requirements", "missing#requirements"))
        with self.assertRaisesRegex(ValueError, "unresolved reference"):
            read_book(self.root)

    def test_literal_prose_fails_build(self):
        p = self.root / "book/chapters/context-and-identity.yaml"
        p.write_text(p.read_text().replace("text: >-", "text: |-", 1))
        with self.assertRaisesRegex(ValueError, "literal narrative"):
            read_book(self.root)

    def test_duplicate_yaml_keys_fail_build(self):
        p = self.root / "book/chapters/context-and-identity.yaml"
        p.write_text(p.read_text() + "\ntitle: duplicate\n")
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            read_book(self.root)

    def test_unlisted_publication_content_fails_build(self):
        shutil.copy(self.root / "book/chapters/detection.yaml", self.root / "book/chapters/forgotten.yaml")
        with self.assertRaisesRegex(ValueError, "unlisted publication"):
            read_book(self.root)

    def test_undeclared_domain_key_fails_build(self):
        p = self.root / "book/chapters/context-and-identity.yaml"
        p.write_text(p.read_text() + "\nsecret_heading: must not be guessed\n")
        with self.assertRaisesRegex(ValueError, "undeclared domain"):
            read_book(self.root)


if __name__ == "__main__":
    unittest.main()
