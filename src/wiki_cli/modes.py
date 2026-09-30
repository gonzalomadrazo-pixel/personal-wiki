"""The three interaction modes. The harness enforces their differences:

search: retrieval tool only. Shows original passages; no model call, no answer.
ask:    standalone RAG. Retrieve passages → research rules + passages → Gemma → citation check.
        Never sees chat history or the persona.
chat:   persona + recent conversation. Retrieves notes only when the turn needs them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import INDEX_MD, Settings, load_prompt, load_taxonomy
from .index import Hit, Retriever
from .llm import ChatResult, OllamaClient

CITE_RE = re.compile(r"\[S(\d+)\]")
INSUFFICIENT = "INSUFFICIENT EVIDENCE"


# ---------------------------------------------------------------------- shared
def format_passages(hits: list[Hit]) -> str:
    blocks = []
    for n, h in enumerate(hits, 1):
        p = h.passage
        loc = f", {p.pages}" if p.pages else ""
        blocks.append(f"[S{n}] {p.title} — section \"{p.section}\"{loc} (file: {p.path})\n{p.text}")
    return "\n\n".join(blocks)


@dataclass
class CitationCheck:
    status: str                      # answered | insufficient | uncited
    cited: list[int] = field(default_factory=list)
    invalid: list[int] = field(default_factory=list)
    uncited_sentences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


def check_citations(answer: str, n_passages: int) -> CitationCheck:
    """Harness-side check: are citations present, and do they point at passages we actually sent?"""
    text = answer.strip()
    cited = sorted({int(m) for m in CITE_RE.findall(text)})
    invalid = [c for c in cited if c < 1 or c > n_passages]
    if text.upper().startswith(INSUFFICIENT):
        return CitationCheck("insufficient", cited, invalid)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if len(s.strip()) > 25]
    uncited = [s for s in sentences if not CITE_RE.search(s)]
    status = "answered" if cited and not invalid else "uncited"
    return CitationCheck(status, cited, invalid, uncited)


# ---------------------------------------------------------------------- search
def run_search(retriever: Retriever, query: str, k: int, include_wiki: bool) -> list[Hit]:
    kinds = ("source", "wiki") if include_wiki else ("source",)
    return retriever.search(query, k, kinds)


# ---------------------------------------------------------------------- ask
@dataclass
class AskResult:
    question: str
    hits: list[Hit]
    answer: str
    check: CitationCheck
    stats: dict
    prompt_chars: int


def run_ask(client: OllamaClient, retriever: Retriever, settings: Settings, question: str,
            k: int | None = None, stream_to=None) -> AskResult:
    hits = retriever.search(question, k or settings.top_k, ("source",))   # original evidence only
    rules = load_prompt("wiki-instructions.md")
    if hits:
        context = format_passages(hits)
    else:
        context = "(no passages matched the question)"
    user = f"QUESTION: {question}\n\nSOURCE PASSAGES:\n{context}\n\nAnswer using only the passages above, following the rules."
    messages = [{"role": "system", "content": rules}, {"role": "user", "content": user}]   # no history, no persona
    result: ChatResult = client.chat(settings.chat_model, messages, stream_to=stream_to,
                                     options={"temperature": settings.ask_temperature, "num_ctx": settings.ask_num_ctx})
    check = check_citations(result.text, len(hits))
    return AskResult(question, hits, result.text.strip(), check, result.stats, len(rules) + len(user))


# ---------------------------------------------------------------------- chat
META_PATTERNS = [
    r"\bwhat can (you|we|i)\b", r"\bhelp me with\b", r"\bwho are you\b", r"\bwhat do you do\b",
    r"^(hi|hello|hey|thanks|thank you|ok|okay|cool|great)\b", r"\bhow do(es)? (this|you) work\b",
]
FOLLOWUP_PATTERNS = [
    r"\b(make|keep) (that|it|this) (shorter|longer|simpler|clearer|punchier)\b", r"^(shorter|simpler|rewrite|rephrase)\b",
    r"\b(turn|convert) (that|it|this) into\b", r"\b(shorten|summari[sz]e|tighten|condense) (that|it|this)\b",
    r"\bmake (that|it|this) (a|an|into)\b", r"\b(bullet|bullets|table) (form|version)\b",
]
OVERVIEW_PATTERNS = [r"\bmain (ideas|themes|topics)\b", r"\boverview\b", r"\bstudy plan\b", r"\bwhole wiki\b",
                     r"\b(all|everything in) (of )?(my|the) notes\b", r"\bwhat('s| is) in (my|the) (notes|wiki)\b"]
NOTES_PATTERNS = [r"\b(my|the) notes\b", r"\bsources?\b", r"\baccording to\b", r"\bwhat did .+ (say|write|argue|think)\b",
                  r"\bin the (letter|memo|transcript)s?\b", r"\bcite\b"]


@dataclass
class RetrievalDecision:
    retrieve: bool
    reason: str
    query: str = ""
    wiki_map: bool = False      # overview requests get the wiki's topic map instead of passages


class ChatSession:
    def __init__(self, client: OllamaClient, retriever: Retriever | None, settings: Settings):
        self.client, self.retriever, self.settings = client, retriever, settings
        self.system = load_prompt("persona.md")
        self.history: list[dict] = []          # conversation context: user + assistant turns only
        self.last_hits: list[Hit] = []
        tax = load_taxonomy()
        terms = []
        for item in tax["concept"] + tax["person"]:
            terms += [item["name"].lower()] + [a.lower() for a in item.get("aliases", [])]
        self.topic_terms = sorted(set(terms), key=len, reverse=True)

    def decide(self, message: str) -> RetrievalDecision:
        """Decide whether this turn needs a notes lookup. Rules are explicit so behaviour is inspectable."""
        text = message.strip()
        low = text.lower()
        if low.startswith("/notes"):
            q = text[len("/notes"):].strip()
            return RetrievalDecision(bool(q), "explicit /notes command", q)
        if any(re.search(p, low) for p in FOLLOWUP_PATTERNS):
            return RetrievalDecision(False, "follow-up edit of the conversation")
        if any(re.search(p, low) for p in META_PATTERNS) and not any(re.search(p, low) for p in NOTES_PATTERNS):
            return RetrievalDecision(False, "conversational / capability question")
        if any(re.search(p, low) for p in OVERVIEW_PATTERNS):
            return RetrievalDecision(False, "overview request: sending the wiki map (index.md), not passages",
                                     wiki_map=True)
        if self.retriever is None:
            return RetrievalDecision(False, "no index available")
        term = next((t for t in self.topic_terms if re.search(rf"\b{re.escape(t)}\b", low)), None)
        if any(re.search(p, low) for p in NOTES_PATTERNS):
            return RetrievalDecision(True, "asks about the notes/sources", text)
        if term:
            return RetrievalDecision(True, f"mentions wiki topic '{term}'", text)
        # Fallback for information questions about topics outside the taxonomy. Requests such as
        # "can you help me write…" are excluded: common words matched notes too easily (unit test).
        if re.match(r"(what|why|how|who|when|where|which|does|did|do|is|are|was|were)\b", low) and "?" in text:
            best = self.retriever.best_bm25(text)
            if best >= self.settings.chat_retrieval_min_bm25:
                return RetrievalDecision(True, f"information question with strong keyword match (bm25 {best:.1f})", text)
        return RetrievalDecision(False, "general conversation; notes not needed")

    def turn(self, message: str, stream_to=None) -> tuple[str, RetrievalDecision, list[Hit], dict]:
        decision = self.decide(message)
        user_text = message[len("/notes"):].strip() if message.lower().startswith("/notes") else message
        hits: list[Hit] = []
        if decision.retrieve and self.retriever is not None:
            hits = self.retriever.search(decision.query, self.settings.chat_top_k, ("source",))
            self.last_hits = hits
        recent = self.history[-self.settings.history_messages:]
        if hits:
            content = (f"{user_text}\n\n---\nPassages from my notes found by the local search tool:\n\n"
                       f"{format_passages(hits)}\n\n---\nReply to my message above. Every point you take from "
                       f"these passages must carry its [S#] citation right after it.")
        elif decision.wiki_map:
            content = f"{user_text}\n\n---\nWIKI MAP (topics and sources in my wiki; not evidence):\n\n{wiki_map()}"
        else:
            content = user_text
        messages = [{"role": "system", "content": self.system}, *recent, {"role": "user", "content": content}]
        result = self.client.chat(self.settings.chat_model, messages, stream_to=stream_to,
                                  options={"temperature": self.settings.chat_temperature,
                                           "num_ctx": self.settings.chat_num_ctx})
        # store the plain user message (not the passages) so old evidence doesn't pile up in context
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": result.text.strip()}]
        return result.text.strip(), decision, hits, result.stats

    def reset(self) -> None:
        self.history.clear()
        self.last_hits = []


def wiki_map() -> str:
    """The concept and source lists from index.md, without link syntax or the machine catalog."""
    if not INDEX_MD.exists():
        return "(wiki not built yet)"
    text = INDEX_MD.read_text()
    start = text.find("## Concepts by topic")
    end = text.find("## Source catalog")
    body = text[start:end if end != -1 else None]
    return re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", body).strip()
