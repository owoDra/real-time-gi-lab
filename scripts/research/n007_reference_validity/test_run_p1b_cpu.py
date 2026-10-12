#!/usr/bin/env python3
"""N007 native-tool path resolution tests (no GPU, no private capture)."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from run_p1b_cpu import resolve_native_binary

class BinaryResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.build=Path(self.tmp.name)
        self.nested=self.build/'src/research/n007_reference_validity'
        self.nested.mkdir(parents=True)
        self.name='phos-n007-cpu-test'

    def test_regular_cmake_subdirectory(self):
        path=self.nested/self.name
        path.touch()
        self.assertEqual(resolve_native_binary(self.build,self.name),path.resolve())

    def test_flat_output_fallback(self):
        path=self.build/self.name
        path.touch()
        self.assertEqual(resolve_native_binary(self.build,self.name),path.resolve())

    def test_prefer_n007_subdir_to_stale_flat_binary(self):
        root=self.build/self.name
        nested=self.nested/self.name
        root.touch()
        nested.touch()
        self.assertEqual(resolve_native_binary(self.build,self.name),nested.resolve())

    def test_missing_file_lists_both_checked_paths(self):
        with self.assertRaisesRegex(ValueError,'src/research/n007_reference_validity'):
            resolve_native_binary(self.build,self.name)

    def test_reject_relative_path_escape(self):
        with self.assertRaisesRegex(ValueError,'invalid N007 native binary name'):
            resolve_native_binary(self.build,'../phos-n007-cpu-test')

if __name__=='__main__':
    unittest.main()
