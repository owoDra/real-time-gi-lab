from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from resume_p1_pilot import load_old_campaign, relative_file


class TestP1aRepair(unittest.TestCase):
    def test_refuses_parent_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "invalid file reference"):
                relative_file(Path(directory), "../reference-8bounce.pfm")

    def test_refuses_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "invalid file reference"):
                relative_file(Path(directory), "/tmp/reference-8bounce.pfm")

    def test_refuses_unverified_previous_pilot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory)
            (old / "n006-p1-pilot-summary.json").write_text(
                json.dumps({
                    "protocol_version": "n006-p1-causal-pilot-v1",
                    "status": "complete",
                    "formal": False,
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "provenance/status"):
                load_old_campaign(old, "AMD Radeon 8060S Graphics (RADV STRIX_HALO)",
                                  "a" * 64)


if __name__ == "__main__":
    unittest.main()
