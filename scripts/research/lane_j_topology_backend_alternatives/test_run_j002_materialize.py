from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_j002_materialize as materialize


class J002MaterializeTests(unittest.TestCase):
    def config(self) -> dict:
        return {
            "producer_source": {
                "case": "static",
                "accepted_git_commit": "abc123",
                "artifact_glob": "out/**/stream-v1.bin",
            }
        }

    def write_candidate(
        self,
        root: Path,
        name: str,
        *,
        case: str,
        commit: str,
    ) -> Path:
        directory = root / "out" / name
        directory.mkdir(parents=True)
        stream = directory / "stream-v1.bin"
        stream.write_bytes(b"stream")
        (directory / "stream-v1.json").write_text(
            json.dumps({
                "case": case,
                "git_commit": commit,
            }),
            encoding="utf-8",
        )
        return stream

    def test_discovers_exact_accepted_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = self.write_candidate(
                root,
                "accepted",
                case="static",
                commit="abc123",
            )
            self.write_candidate(
                root,
                "wrong-case",
                case="camera-motion",
                commit="abc123",
            )
            self.write_candidate(
                root,
                "wrong-commit",
                case="static",
                commit="other",
            )
            self.assertEqual(
                materialize.discover_accepted_producer_stream(
                    root,
                    self.config(),
                ),
                expected,
            )

    def test_rejects_ambiguous_accepted_streams(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_candidate(
                root,
                "one",
                case="static",
                commit="abc123",
            )
            self.write_candidate(
                root,
                "two",
                case="static",
                commit="abc123",
            )
            with self.assertRaises(RuntimeError):
                materialize.discover_accepted_producer_stream(
                    root,
                    self.config(),
                )


if __name__ == "__main__":
    unittest.main()
