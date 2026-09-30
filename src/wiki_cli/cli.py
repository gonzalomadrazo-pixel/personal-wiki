"""`wiki` command-line interface: the user's entry point into the harness.

One path through the code (wiki ask "..."):
  main() parses args → cmd_ask() → Retriever.search() finds source passages (BM25 + embeddings)
  → modes.run_ask() builds [research rules] + [question + numbered passages] (no chat history)
  → OllamaClient.chat() calls local Gemma → modes.check_citations() verifies [S#] citations
  → answer, sources and checks are printed, and the full record is saved to runs/ask/.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import time
from pathlib import Path

from . import __version__
from .config import EVIDENCE, INDEX_DIR, RAW, ROOT, RUNS, load_settings
from .evidence import append_jsonl, save_run, slug
from .index import Retriever, build_index
from .llm import LLMError, OllamaClient, network_status

TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if TTY else text


dim = lambda t: c("2", t)          # noqa: E731
bold = lambda t: c("1", t)         # noqa: E731
green = lambda t: c("32", t)       # noqa: E731
yellow = lambda t: c("33", t)      # noqa: E731
red = lambda t: c("31", t)         # noqa: E731
cyan = lambda t: c("36", t)        # noqa: E731


def header(mode: str, settings, extra: str = "") -> None:
    host = settings.ollama_host.replace("http://", "")
    print(dim(f"wiki {__version__} · mode: {mode} · execution: local · model: {settings.chat_model} "
              f"(Ollama @ {host}){extra}"))


def wrap(text: str, indent: str = "  ") -> str:
    out = []
    for para in text.splitlines():
        out.append(textwrap.fill(para, width=100, initial_indent=indent, subsequent_indent=indent) if para.strip() else "")
    return "\n".join(out)


def print_hits(hits, show_scores: bool = True) -> None:
    for n, h in enumerate(hits, 1):
        p = h.passage
        loc = f" · {p.pages}" if p.pages else ""
        score = f"  bm25={h.bm25:.2f}" + (f" cos={h.cosine:.3f}" if h.cosine is not None else "") if show_scores else ""
        tag = "" if p.kind == "source" else yellow(" [generated wiki page]")
        print(f"\n{cyan(f'[S{n}]')} {bold(p.title)} — {p.section}{loc}{tag}")
        print(dim(f"     vault/{p.path}{score}"))
        print(wrap(p.text, "     "))


def local_only(mode: str) -> None:
    if mode != "local":
        raise SystemExit(red("Online mode is an optional extension that this project does not implement. "
                             "Use --mode local (the default); everything runs on this computer."))


# ---------------------------------------------------------------------- commands
def cmd_ingest(args, settings) -> int:
    from .ingest import ingest
    header("ingest", settings)
    client = OllamaClient.from_settings(settings)
    target = Path(args.path)
    print(f"Ingesting {target} …")
    report = ingest(target, settings, client, force=args.force)
    print(f"Rendered {report['pages_written']} pages (wiki/Sources, wiki/Concepts, wiki/Investors, index.md); "
          f"removed {len(report['pages_removed'])} stale generated pages.")
    print("Rebuilding retrieval index …")
    stats = build_index(settings, client)
    report["index"] = stats
    report["memory"] = ollama_memory(client)
    print(f"Index: {stats['source_passages']} source passages + {stats['wiki_passages']} wiki passages, "
          f"{stats['embedded']} embedded ({stats['newly_embedded']} new).")
    path = save_run("ingest", target.name, report)
    print(dim(f"Saved ingest report → {path.relative_to(ROOT)}  ·  total {report['seconds']}s"))
    print(dim("Review flagged statements in data/reviews/*.md before trusting the wiki pages."))
    return 0


def cmd_index(args, settings) -> int:
    header("index", settings)
    client = OllamaClient.from_settings(settings)
    stats = build_index(settings, client if client.is_up() else None)
    print(json.dumps(stats, indent=2))
    return 0


def cmd_search(args, settings) -> int:
    client = OllamaClient.from_settings(settings)
    retriever = Retriever(settings, client if client.is_up() else None)
    from .modes import run_search
    t0 = time.perf_counter()
    hits = run_search(retriever, args.query, args.k, args.include_wiki)
    header("search (retrieval only, no generation)", settings,
           f" · {retriever.embedding_note or 'hybrid BM25 + embeddings'}")
    print(f"{bold('Query:')} {args.query}")
    if not hits:
        print(yellow("No matching passages."))
    print_hits(hits)
    elapsed = round(time.perf_counter() - t0, 2)
    print(dim(f"\n{len(hits)} passages in {elapsed}s. No answer is generated in search mode."))
    if not args.no_save:
        path = save_run("search", args.query, {"query": args.query, "include_wiki": args.include_wiki,
                                                "retrieval": retriever.embedding_note or "hybrid BM25 + embeddings",
                                                "seconds": elapsed, "results": [h.to_dict() for h in hits]})
        print(dim(f"Saved → {path.relative_to(ROOT)}"))
    return 0


def cmd_ask(args, settings) -> int:
    local_only(args.mode)
    from .modes import run_ask
    client = OllamaClient.from_settings(settings)
    if not client.is_up():
        raise LLMError(f"Cannot reach the local Ollama server at {settings.ollama_host}.\n"
                       "Start it by opening the Ollama app or running:  ollama serve   "
                       "(wiki search still works without it)")
    retriever = Retriever(settings, client)
    header("ask (standalone, evidence only)", settings)
    print(f"{bold('Question:')} {args.question}\n")
    print(bold("Answer:"))
    sys.stdout.write("  ")
    res = run_ask(client, retriever, settings, args.question, args.k,
                  stream_to=lambda t: (sys.stdout.write(t.replace("\n", "\n  ")), sys.stdout.flush()))
    print("\n")
    chk = res.check
    if chk.status == "insufficient":
        print(yellow("Citation check: model reported INSUFFICIENT EVIDENCE (no answer asserted)."))
    elif chk.status == "answered":
        print(green(f"Citation check: cites {', '.join(f'[S{i}]' for i in chk.cited)}; all point to retrieved passages."))
        if chk.uncited_sentences:
            print(yellow(f"  ! {len(chk.uncited_sentences)} sentence(s) without a citation: "
                         + " | ".join(s[:60] + '…' for s in chk.uncited_sentences)))
    else:
        print(red(f"Citation check FAILED: {'invalid citations ' + str(chk.invalid) if chk.invalid else 'no citations'}. "
                  "Treat this answer as unsupported."))
    print(bold("\nSources:"))
    for n, h in enumerate(res.hits, 1):
        mark = green("cited") if n in chk.cited else dim("not cited")
        p = h.passage
        print(f"  [S{n}] vault/{p.path} › {p.section}{', ' + p.pages if p.pages else ''}  ({mark})")
    s = res.stats
    print(dim(f"\n{s['wall_seconds']}s total · {s['prompt_tokens']} prompt tokens · {s['output_tokens']} output tokens"
              f" · {s['tokens_per_second']} tok/s · load {s['load_seconds']}s"))
    if args.show_passages:
        print(bold("\nRetrieved passages:"))
        print_hits(res.hits)
    if not args.no_save:
        path = save_run("ask", args.question, {
            "question": args.question, "model": settings.chat_model, "chat_history_used": False,
            "instructions": "prompts/wiki-instructions.md", "retrieved": [h.to_dict() for h in res.hits],
            "answer": res.answer, "citation_check": chk.to_dict(), "stats": s, "prompt_chars": res.prompt_chars})
        print(dim(f"Saved → {path.relative_to(ROOT)}"))
    return 0


CHAT_HELP = """Commands: /notes <topic> force a notes lookup · /sources show passages used last · /save [name] save last reply
          /history show context · /reset clear conversation · /help · /exit"""


def cmd_chat(args, settings) -> int:
    local_only(args.mode)
    from .modes import ChatSession
    client = OllamaClient.from_settings(settings)
    if not client.is_up():
        raise LLMError(f"Cannot reach the local Ollama server at {settings.ollama_host}. Open the Ollama app or run: ollama serve")
    try:
        retriever = Retriever(settings, client)
    except FileNotFoundError:
        retriever = None
    session = ChatSession(client, retriever, settings)
    session_file = RUNS / "chat" / f"{time.strftime('%Y%m%d-%H%M%S')}-session.jsonl"
    header("chat (personal assistant)", settings)
    print(bold("Ledger") + " — your study partner for the investing wiki. " + dim(CHAT_HELP))
    scripted = None
    if args.script:
        scripted = [l.rstrip("\n") for l in Path(args.script).read_text().splitlines() if l.strip() and not l.startswith("#")]
    last_reply = ""
    while True:
        try:
            if scripted is not None:
                if not scripted:
                    break
                msg = scripted.pop(0)
                print(f"\n{bold('you ›')} {msg}")
            else:
                msg = input(f"\n{bold('you ›')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue
        cmd = msg.split()[0].lower()
        if cmd in ("/exit", "/quit"):
            break
        if cmd == "/help":
            print(dim(CHAT_HELP))
            continue
        if cmd == "/reset":
            session.reset()
            print(dim("Conversation cleared."))
            continue
        if cmd == "/history":
            for m in session.history:
                print(dim(f"  {m['role']}: {m['content'][:120]}"))
            continue
        if cmd == "/sources":
            print_hits(session.last_hits) if session.last_hits else print(dim("No notes were used yet."))
            continue
        if cmd == "/save":
            if not last_reply:
                print(dim("Nothing to save yet."))
                continue
            name = slug(" ".join(msg.split()[1:]) or "draft")
            out = ROOT / "drafts" / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}.md"
            out.parent.mkdir(exist_ok=True)
            out.write_text(f"<!-- chat draft (generated, not source evidence) -->\n\n{last_reply}\n")
            print(dim(f"Saved draft → {out.relative_to(ROOT)} (kept outside the vault; not evidence)"))
            continue
        sys.stdout.write(f"{bold('ledger ›')} ")
        reply, decision, hits, stats = session.turn(
            msg, stream_to=lambda t: (sys.stdout.write(t), sys.stdout.flush()))
        last_reply = reply
        if hits:
            cited = "cited inline" if re.search(r"\[S\d+\]", reply) else "reply did not cite them inline"
            print("\n" + dim(f"  ↳ looked up notes ({decision.reason}); {cited} · {stats['wall_seconds']}s"))
            for i, h in enumerate(hits, 1):
                p = h.passage
                print(dim(f"     [S{i}] vault/{p.path} › {p.section}{', ' + p.pages if p.pages else ''}"))
        else:
            print("\n" + dim(f"  ↳ no notes lookup ({decision.reason}) · {stats['wall_seconds']}s"))
        append_jsonl(session_file, {"mode": "chat", "execution": "local", "model": settings.chat_model,
                                    "user": msg, "retrieval": decision.__dict__,
                                    "passages": [h.to_dict() for h in hits], "reply": reply, "stats": stats,
                                    "history_messages_sent": min(len(session.history) - 2, settings.history_messages)})
    print(dim(f"Session saved → {session_file.relative_to(ROOT)}" if session_file.exists() else "Bye."))
    return 0


def ollama_memory(client: OllamaClient) -> list[dict]:
    try:
        return [{"model": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 2),
                 "gpu_gb": round(m.get("size_vram", 0) / 1e9, 2), "context": m.get("context_length")}
                for m in client.ps()]
    except LLMError:
        return []


def runner_footprint() -> str:
    """Physical memory footprint of Ollama's model process as macOS reports it (top's MEM column).
    `ollama ps` only shows the GPU-resident part of the model, which understates real memory use."""
    try:
        out = subprocess.run(["top", "-l", "1", "-o", "mem", "-n", "15", "-stats", "command,mem"],
                             capture_output=True, text=True, timeout=10).stdout
        rows = [l.split() for l in out.splitlines() if l.startswith(("llama-server", "ollama"))]
        return ", ".join(f"{r[0]} {r[1]}" for r in rows) or "no Ollama model process running"
    except Exception:
        return "unknown"


def cmd_status(args, settings) -> int:
    header("status", settings)
    client = OllamaClient.from_settings(settings)
    up = client.is_up()
    print(f"Ollama server:   {green('running') if up else red('not reachable — open the Ollama app or run: ollama serve')}")
    if up:
        for model in (settings.chat_model, settings.embed_model):
            try:
                info = client.model_info(model)
                print(f"Model:           {model}  [{info['family']}, {info['parameter_size']}, {info['quantization']}, "
                      f"digest {info['digest']}]  {info['runtime']}")
            except LLMError as e:
                print(red(f"Model:           {e}"))
        mem = ollama_memory(client)
        print(f"Loaded now:      {', '.join(f'{m['model']} {m['size_gb']} GB (GPU {m['gpu_gb']} GB, ctx {m['context']})' for m in mem) or 'nothing loaded'}")
        print(f"Process memory:  {runner_footprint()}  (macOS footprint)")
        pressure = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()
        print(f"System memory:   {pressure[-1] if pressure else 'unknown'}")
    stats = INDEX_DIR / "stats.json"
    print(f"Index:           {json.loads(stats.read_text()) if stats.exists() else red('missing — run: wiki ingest vault/raw')}")
    print(f"Raw sources:     {len(list(RAW.glob('*.md')))} notes in vault/raw/")
    if args.check_network:
        print(f"Network:         {network_status()}")
    return 0


def cmd_eval(args, settings) -> int:
    from .evals import run_evals
    header("eval (ask-mode tests)", settings)
    client = OllamaClient.from_settings(settings)
    run_evals(Path(args.file), settings, client, EVIDENCE / "ask-tests", log=print)
    return 0


# ---------------------------------------------------------------------- parser
EPILOG = """\
modes
  search   retrieval only: shows original passages + file paths, never generates text (works without Gemma)
  ask      standalone factual answer from retrieved evidence with [S#] citations, or INSUFFICIENT EVIDENCE;
           ignores chat history and personality
  chat     personal assistant (persona in prompts/persona.md) with conversation memory; looks up notes only
           when a turn needs them

inputs & configuration
  vault/raw/*.md           original study notes (unchanged evidence). Put new sources here, then run ingest.
  config/settings.toml     model names, context sizes, passage size, top-k (env: WIKI_MODEL, OLLAMA_HOST)
  config/taxonomy.toml     allowed concept / investor page names and their human-written link reasons
  prompts/*.md             persona.md (chat), wiki-instructions.md (ask), ingest-instructions.md (ingest)

requirements
  Ollama running locally with:  ollama pull gemma4:e2b-it-qat   and   ollama pull nomic-embed-text

examples
  wiki ingest vault/raw
  wiki search "Mr. Market"
  wiki ask "How does Howard Marks define risk?" --mode local
  wiki chat
  wiki status --check-network
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki", description="Personal investing wiki — local Gemma + RAG harness.",
                                epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"wiki {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    s = sub.add_parser("ingest", help="read sources, generate linked wiki pages with Gemma, update index.md and the search index")
    s.add_argument("path", nargs="?", default=str(RAW), help="file or folder inside vault/raw (default: vault/raw)")
    s.add_argument("--force", action="store_true", help="re-run Gemma even for unchanged sources; for reviewed sources the new output is saved as a .candidate for comparison")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("search", help="show matching original passages and paths (no generation)")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5, help="number of passages (default 5)")
    s.add_argument("--include-wiki", action="store_true", help="also search generated wiki pages")
    s.add_argument("--no-save", action="store_true", help="don't write a record to runs/search/")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("ask", help="standalone cited answer from your sources, or INSUFFICIENT EVIDENCE")
    s.add_argument("question")
    s.add_argument("--mode", choices=["local", "online"], default="local", help="where the model runs (default: local)")
    s.add_argument("-k", type=int, default=None, help="passages to retrieve (default from settings: 5)")
    s.add_argument("--show-passages", action="store_true", help="print the full retrieved passages after the answer")
    s.add_argument("--no-save", action="store_true", help="don't write a record to runs/ask/")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("chat", help="personal assistant with conversation memory and on-demand notes lookup")
    s.add_argument("--mode", choices=["local", "online"], default="local")
    s.add_argument("--script", help="read user turns from a text file (one per line) instead of the keyboard")
    s.set_defaults(func=cmd_chat)

    s = sub.add_parser("index", help="rebuild only the retrieval index from vault/raw and vault/wiki")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("status", help="show model, runtime, memory use and index status")
    s.add_argument("--check-network", action="store_true", help="also report whether the internet is reachable")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("eval", help="run the ask-mode test questions and write evidence cards")
    s.add_argument("file", nargs="?", default=str(ROOT / "evals" / "questions.toml"))
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("help", help="show this help")
    s.set_defaults(func=lambda a, st: (build_parser().print_help(), 0)[1])
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args, load_settings())
    except LLMError as e:
        print(red(f"\nerror: {e}"), file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError) as e:
        print(red(f"error: {e}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
