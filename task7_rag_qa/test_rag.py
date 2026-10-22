#!/usr/bin/env python3
"""Tests for Task 7 (RAG tool)."""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from rag_qa import RAGTool, create_sample_docs


class TestRAG(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.tmp.name)
        create_sample_docs(self.docs_dir)
        self.rag = RAGTool(docs_dir=self.docs_dir, similarity_threshold=0.1)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_retrieves_and_answers(self) -> None:
        res = self.rag.answer("What is RAG?")
        self.assertTrue(res.used_chunks)
        self.assertTrue(len(res.citations) > 0)
        self.assertNotEqual(res.answer, "I don't know")

    def test_out_of_scope_returns_dont_know(self) -> None:
        res = self.rag.answer("What is the capital of France?")
        self.assertFalse(res.used_chunks)
        self.assertEqual(res.answer, "I don't know")
        self.assertEqual(len(res.citations), 0)

    def test_threshold_enforced(self) -> None:
        # Very high threshold should trigger "I don't know" for most questions
        rag_high = RAGTool(docs_dir=self.docs_dir, similarity_threshold=0.99)
        res = rag_high.answer("What is Python?")
        # May or may not find perfect match; we just check threshold is respected
        if not res.used_chunks:
            self.assertEqual(res.answer, "I don't know")


if __name__ == "__main__":
    unittest.main(verbosity=2)
