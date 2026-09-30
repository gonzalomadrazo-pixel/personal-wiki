"""Model-free tests of the harness logic. Run:  PYTHONPATH=src python3 -m unittest discover -s tests -v

They cover the parts that must behave deterministically: how notes become passages, how
citations are checked, when chat decides to look up notes, what retrieval returns, and what
ingestion refuses. None of them call Gemma, so they run in about a second and offline.
"""

import tempfile
import unittest
from pathlib import Path

from wiki_cli.chunking import chunk_note, parse_frontmatter, split_sections
from wiki_cli.config import RAW, VAULT, load_settings
from wiki_cli.index import Retriever, tokenize
from wiki_cli.ingest import find_sources
from wiki_cli.modes import ChatSession, check_citations

NOTE = """---
source_id: demo-note
wiki_title: Demo Note
author: Test Author
---

# Demo Note — study notes

These are my notes on a demo source.

## The workshop (PDF pp. 3-4)

- The workshop starts at 10 a.m. in Room 204.
- Lunch is not mentioned anywhere.

## A long section (PDF p. 9)

""" + "\n".join(f"- Bullet number {i} with several extra words to make it longer than usual." for i in range(40))


class Chunking(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        (self.vault / "raw").mkdir()
        self.path = self.vault / "raw" / "demo-note.md"
        self.path.write_text(NOTE)

    def tearDown(self):
        self.tmp.cleanup()

    def test_frontmatter(self):
        meta, body = parse_frontmatter(NOTE)
        self.assertEqual(meta["source_id"], "demo-note")
        self.assertTrue(body.startswith("# Demo Note"))

    def test_sections_and_pages(self):
        ps = chunk_note(self.path, self.vault, "source", max_words=220)
        self.assertEqual(ps[0].section, "The workshop")
        self.assertEqual(ps[0].pages, "PDF pp. 3-4")
        self.assertEqual(ps[0].path, "raw/demo-note.md")
        self.assertIn("Room 204", ps[0].text)

    def test_short_intro_is_not_indexed(self):
        ps = chunk_note(self.path, self.vault, "source", max_words=220)
        self.assertNotIn("Overview", {p.section for p in ps})

    def test_long_section_is_split_without_breaking_bullets(self):
        ps = [p for p in chunk_note(self.path, self.vault, "source", max_words=220) if p.section == "A long section"]
        self.assertGreater(len(ps), 1)
        for p in ps:
            self.assertLessEqual(len(p.text.split()), 220 + 20)
            self.assertTrue(p.text.startswith("- Bullet"))

    def test_split_sections_keeps_order(self):
        _, body = parse_frontmatter(NOTE)
        names = [h for h, _ in split_sections(body)]
        self.assertEqual(names, ["Overview", "The workshop (PDF pp. 3-4)", "A long section (PDF p. 9)"])


class Citations(unittest.TestCase):
    def test_answered(self):
        c = check_citations("The workshop is in Room 204 [S1]. It starts at 10 a.m. [S1][S2].", 3)
        self.assertEqual(c.status, "answered")
        self.assertEqual(c.cited, [1, 2])

    def test_invalid_citation_fails(self):
        c = check_citations("The workshop is in Room 204 [S7].", 3)
        self.assertEqual(c.status, "uncited")
        self.assertEqual(c.invalid, [7])

    def test_insufficient(self):
        c = check_citations("INSUFFICIENT EVIDENCE\nThe passages do not say who caters.", 3)
        self.assertEqual(c.status, "insufficient")

    def test_uncited_sentence_is_listed(self):
        c = check_citations("The workshop is in Room 204 [S1]. Everyone will surely love the catering there.", 3)
        self.assertEqual(c.status, "answered")
        self.assertEqual(len(c.uncited_sentences), 1)


class Retrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.retriever = Retriever(cls.settings, client=None)   # BM25 only: no model needed

    def test_tokenize_stems_plurals(self):
        self.assertEqual(tokenize("Cycles companies"), ["cycle", "company"])

    def test_rule_of_three_is_found(self):
        hits = self.retriever.search("Rule of Three", 3)
        self.assertEqual(hits[0].passage.source_id, "rochon-2002-giverny-letter")
        self.assertEqual(hits[0].passage.section, "The Rule of Three")

    def test_ask_retrieval_excludes_generated_pages(self):
        hits = self.retriever.search("Mr Market", 6, ("source",))
        self.assertTrue(all(h.passage.path.startswith("raw/") for h in hits))

    def test_every_source_passage_is_traceable(self):
        for p in self.retriever.passages:
            if p.kind == "source":
                self.assertTrue((VAULT / p.path).exists(), p.path)
                self.assertTrue(p.pages.startswith("PDF p"), f"{p.id} has no PDF page reference")


class ChatRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings = load_settings()
        cls.chat = ChatSession(client=None, retriever=Retriever(settings, None), settings=settings)

    def check(self, msg, retrieve, map_=False):
        d = self.chat.decide(msg)
        self.assertEqual((d.retrieve, d.wiki_map), (retrieve, map_), f"{msg!r} → {d.reason}")

    def test_capability_questions_do_not_retrieve(self):
        self.check("what can we do?", False)
        self.check("what can you help me with?", False)
        self.check("hi", False)

    def test_follow_up_edits_use_conversation(self):
        self.check("make that shorter", False)
        self.check("turn that into flashcards", False)

    def test_overview_uses_wiki_map(self):
        self.check("Draft a 5-day study plan for the main ideas in my notes", False, map_=True)

    def test_topic_questions_retrieve(self):
        self.check("What does Buffett mean by Mr. Market?", True)
        self.check("How does the credit cycle work?", True)
        self.check("/notes circle of competence", True)

    def test_general_chat_does_not_retrieve(self):
        self.check("Can you help me write an email to my study group about Thursday?", False)
        self.check("I'm tired, let's keep this short today.", False)

    def test_information_question_outside_taxonomy_retrieves(self):
        self.check("Why did Berkshire buy the Salomon preferred stock?", True)
        self.check("What happened to Sun Microsystems after Rochon sold it?", True)


class IngestGuards(unittest.TestCase):
    def test_rejects_missing_path(self):
        with self.assertRaises(FileNotFoundError):
            find_sources(RAW / "does-not-exist.md")

    def test_rejects_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            with self.assertRaises(ValueError):
                find_sources(Path(f.name))

    def test_rejects_files_outside_raw(self):
        with tempfile.NamedTemporaryFile(suffix=".md") as f:
            with self.assertRaises(ValueError):
                find_sources(Path(f.name))

    def test_finds_all_raw_notes(self):
        self.assertEqual(len(find_sources(RAW)), 9)


if __name__ == "__main__":
    unittest.main()
