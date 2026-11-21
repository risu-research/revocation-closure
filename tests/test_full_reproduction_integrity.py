#!/usr/bin/env python3
"""Negative controls for archived-evidence SHA-256 verification."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_full_reproduction_artifacts import verify_sha256_manifest


class ArchivedHashNegativeControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.group = self.root / "synthetic-group"
        self.group.mkdir()
        self.evidence = self.group / "evidence.sqlite"
        self.evidence.write_bytes(b"fixed synthetic evidence")
        self.manifest = self.group / "SHA256SUMS.txt"
        self.write_manifest("evidence.sqlite")

    def write_manifest(self, relative_name):
        digest = hashlib.sha256(self.evidence.read_bytes()).hexdigest()
        self.manifest.write_text(f"{digest}  {relative_name}\n", encoding="utf-8")

    def test_valid_evidence_is_accepted(self):
        self.assertEqual(verify_sha256_manifest(self.manifest, self.root), 1)

    def test_modified_evidence_is_rejected(self):
        self.evidence.write_bytes(b"altered synthetic evidence")
        with self.assertRaises(AssertionError):
            verify_sha256_manifest(self.manifest, self.root)

    def test_missing_evidence_is_rejected(self):
        self.evidence.unlink()
        with self.assertRaises(AssertionError):
            verify_sha256_manifest(self.manifest, self.root)

    def test_path_outside_archive_is_rejected(self):
        self.write_manifest("../../outside-evidence.txt")
        with self.assertRaises(AssertionError):
            verify_sha256_manifest(self.manifest, self.root)

    def test_empty_manifest_is_rejected(self):
        self.manifest.write_text("", encoding="utf-8")
        with self.assertRaises(AssertionError):
            verify_sha256_manifest(self.manifest, self.root)

    def test_malformed_digest_is_rejected(self):
        self.manifest.write_text("broken-hash  evidence.sqlite\n", encoding="utf-8")
        with self.assertRaises(AssertionError):
            verify_sha256_manifest(self.manifest, self.root)


if __name__ == "__main__":
    unittest.main()
