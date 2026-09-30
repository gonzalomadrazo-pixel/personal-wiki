"""One-off human review of Gemma's extractions (2026-09-29).

Each correction is written to data/extractions/<id>.json (marked reviewed) and logged in
data/reviews/<id>.md, so the wiki is fixed without touching the original notes in vault/raw/.
Re-ingestion keeps reviewed extractions unless the source note itself changes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = "Claude (AI assistant) checked every statement against the note on 2026-09-29; Gonzalo to confirm"

# (source_id, field, match-prefix or concept name, new text or None to delete, reason)
FIXES = [
    ("buffett-1987-letter", "kp", "Mr. Market is an emotional partner",
     "Mr. Market is an emotional partner whose prices the investor may use or ignore, but whose opinions should never guide the investor's judgment of value.",
     "Gemma said prices 'should be ignored'; the note says you may ignore OR take advantage of them; he is there to serve, not guide."),
    ("buffett-1987-letter", "concept", "Mr Market",
     "Buffett retells Graham's allegory of Mr. Market, an emotional partner whose quotes swing between euphoria and depression; the investor is free to ignore him or take advantage of him, but must never fall under his influence.",
     "Same misreading: 'ignore his prices' → use or ignore, never be guided."),
    ("buffett-1987-letter", "concept", "Capital Allocation",
     "Buffett notes that many CEOs rise through marketing, production or administration and are not skilled at capital allocation, yet a CEO whose company retains 10% of net worth a year will have deployed more than 60% of its capital after ten years.",
     "Replaced vague 'a certain percentage / significant portion' with the note's figures."),
    ("buffett-1987-letter", "concept", "Circle of Competence",
     "Buffett limits Berkshire's choices to investment alternatives it understands, and says that anyone who cannot value their business better than Mr. Market does not belong in the game.",
     "Gemma's text was about insulation from market emotion, not circle of competence; replaced with the note's actual competence statements."),

    ("buffett-1996-letter", "kp", "If an investor does not intend",
     "If you would not own a stock for ten years, don't own it for ten minutes; a portfolio whose combined earnings rise over the years will see its market value rise too.",
     "Gemma garbled the ten-years / ten-minutes rule."),
    ("buffett-1996-letter", "concept", "Owner Earnings",
     "Buffett says a portfolio of companies whose aggregate earnings rise over the years will see its market value rise too, which is how Berkshire's look-through earnings and share price grew together.",
     "Original claim ('buying should be based on earnings rather than quotes') is not stated in the note."),
    ("buffett-1996-letter", "concept", "Competitive Moats",
     "Buffett calls Coca-Cola and Gillette 'The Inevitables', companies almost certain to dominate their fields worldwide for an investment lifetime, and warns that most apparent leaders are 'Impostors' vulnerable to competitive attack.",
     "Replaced a hedged inference ('implying...') with the note's explicit discussion."),
    ("buffett-1996-letter", "concept", "Learning From Mistakes",
     "Buffett calls his 1989 USAir preferred-stock investment a mistake: he trusted the airline's long profit history and missed that deregulated competition had changed its economics, showing a track record can mislead.",
     "Added the concrete USAir example the lesson comes from."),

    ("marks-2001-cycles-memo", "kp_section", "Economic forecasts are generally not valuable", "The economic cycle",
     "Content is from 'The economic cycle' section, not 'Knowing where you are vs. predicting'."),
    ("marks-2001-cycles-memo", "concept", "Price and Value",
     "Marks notes that asset prices often move far more than cash flows because investor psychology changes valuations, and he trims cyclical companies when the market forgets that peak earnings deserve trough valuations.",
     "Made the price/value link explicit and grounded in the note."),
    ("marks-2001-cycles-memo", "concept", "Patience and Long Holding Periods", None,
     "Unsupported: the note never says holding good businesses for years is a source of return."),
    ("marks-2001-cycles-memo", "add_concept", "Contrarian Investing",
     "Marks copes with cycles by leaning against the wind: investing in cyclical companies when the economy is depressed and observers are gloomy, and preferring arenas where others are not throwing money.",
     "Added a concept the note clearly discusses."),

    ("marks-2003-most-important-thing", "kp", "The relationship between price and value is paramount",
     "The relationship between price and value comes first: no asset is so good it can't be a bad investment at too high a price, and few are so bad they can't be good investments when cheap enough.",
     "Gemma overstated it as 'no asset is inherently good or bad'."),
    ("marks-2003-most-important-thing", "concept", "Price and Value",
     "Marks says the relationship between price and value comes first: a good company is not the same as a good investment, and the biggest losses come from buying 'perfect' companies at prices that assume perfection.",
     "Same overstatement fixed."),
    ("marks-2003-most-important-thing", "kp", "Managers should be hired",
     "Oaktree keeps staff turnover low by hiring team players, keeping a collegial culture and sharing ownership, and it values consistent, principled answers over any single answer.",
     "Gemma's sentence was garbled."),
    ("marks-2003-most-important-thing", "concept", "Circle of Competence", None,
     "Unsupported: Gemma itself wrote 'while not explicitly named ... implies'."),
    ("marks-2003-most-important-thing", "concept", "Risk vs Volatility",
     "Marks frames risk control as avoiding losers and bad years ('invest scared'), aiming over time for above-market returns with below-market volatility.",
     "Removed speculative 'implying'; kept only what the note states."),

    ("marks-2006-risk-memo", "concept", "Circle of Competence",
     "Marks argues that whether concentration or illiquidity is risky depends on the investor's knowledge: Buffett and Munger can hold concentrated, illiquid positions because they know what they are doing.",
     "Replaced a vague implication with the note's actual argument."),
    ("marks-2006-risk-memo", "concept", "Mental Models", None,
     "Unsupported: the memo does not discuss mental models."),
    ("marks-2006-risk-memo", "add_concept", "Diversification vs Concentration",
     "Marks says diversification trades return for safety because knowledge of the future is imperfect; concentration is risky for investors who can't see the future clearly, but not for those who can.",
     "Added a concept the memo explicitly discusses."),
    ("marks-2006-risk-memo", "add_concept", "Price and Value",
     "Marks says risky assets can be good investments if they are cheap enough, and the skill lies in knowing when that is the case.",
     "Added a concept the memo explicitly discusses."),

    ("munger-2016-daily-journal", "summary", "",
     "This study note covers the investing parts of Charlie Munger's 2016 Daily Journal Q&A. Munger stresses using multiple mental models, patience followed by decisive action, paying attention to opportunity cost, and staying inside one's circle of competence, and he describes rationality as avoiding anger, envy and self-pity.",
     "Original summary claimed 'rigorous valuation'; the note says valuation is not a formula."),
    ("munger-2016-daily-journal", "kp", "The business landscape is constantly shifting",
     "As Daily Journal's newspaper profits shrank, it used foreclosure-boom cash to buy stocks during the panic and moved into court software, which Munger describes as a slow, venture-capital-like bet.",
     "Replaced a generic statement with the note's specifics."),
    ("munger-2016-daily-journal", "concept", "Owner Earnings", None,
     "Unsupported: the note does not discuss earnings vs. stock quotes."),
    ("munger-2016-daily-journal", "concept", "Competitive Moats",
     "Munger says a software business that becomes entrenched can be very 'sticky', while autos are brutally competitive and commoditised, so an investor there would need a clearly superior competitor.",
     "Replaced a hedged inference with the note's statements."),
    ("munger-2016-daily-journal", "concept", "Price and Value",
     "Munger says fundamental value investing will never go out of style because success requires buying things for less than they are worth; Bank of America was bought after it fell far below its value.",
     "Gemma duplicated the opportunity-cost text here."),

    ("rochon-2002-giverny-letter", "kp", "The market experiences recurring patterns",
     "Rochon's Rule of Three: one year in three the market falls more than 10%, one stock in three disappoints, and one year in three the portfolio lags the indexes; accepting this in advance helps investors stay rational.",
     "Gemma listed only one of the three parts."),
    ("rochon-2002-giverny-letter", "kp", "Investors should use multiple mental models",
     "Echoing Munger's advice to use many mental models, Rochon compares investing to tending Monet's garden at Giverny.",
     "Removed 'rather than a single formula', which is not in the note."),
    ("rochon-2002-giverny-letter", "concept", "Mental Models",
     "Echoing Munger's advice to use many mental models, Rochon compares investing to gardening: know your soil and climate, tend the garden continuously, and don't pull the flowers to water the weeds.",
     "Made specific to the note."),
    ("rochon-2002-giverny-letter", "add_concept", "Circle of Competence",
     "Like Ted Williams swinging only at pitches in his best zones, Rochon waits for companies he can value and ignores sectors such as oil and gold regardless of price.",
     "Added a concept the letter clearly discusses."),

    ("sleep-2006-nomad-letter", "kp", "The index is not a reliable benchmark",
     "Sleep says the index is not Nomad's benchmark, and treating an index as a risk-free home leads to errors like ignoring one's circle of competence and over-diversifying.",
     "Gemma generalised 'not our benchmark' into 'not a reliable benchmark'."),
    ("sleep-2006-nomad-letter", "concept", "Circle of Competence",
     "Sleep says treating an index as a risk-free home makes managers feel they must have an opinion on everything in it, regardless of their circle of competence.",
     "Gemma inverted the point ('failing to have a view on everything')."),
    ("sleep-2006-nomad-letter", "add_concept", "Diversification vs Concentration",
     "Sleep lists over-diversification among the capital-destroying mistakes of index-relative investing; Nomad's top five holdings were about half of the portfolio.",
     "Added a concept the letter clearly discusses."),
    ("sleep-2006-nomad-letter", "add_concept", "Competitive Moats",
     "An earlier Nomad appendix proposed measuring a moat's strength by how a firm splits scale benefits between customers, employees and shareholders (the 'robustness ratio'), using GEICO as the example.",
     "Added a concept the letter clearly discusses."),
]


def main():
    by_source = {}
    for f in FIXES:
        by_source.setdefault(f[0], []).append(f)
    for path in sorted((ROOT / "data/extractions").glob("*.json")):
        if path.name.endswith(".candidate.json"):
            continue
        d = json.loads(path.read_text())
        sid = d["source_id"]
        if d.get("reviewed"):
            print(f"{sid}: already reviewed, skipped")
            continue
        log = []
        for _, field, key, new, why in by_source.get(sid, []):
            if field == "summary":
                d["summary"] = new
            elif field in ("kp", "kp_section"):
                kp = next(k for k in d["key_points"] if k["point"].startswith(key))
                if field == "kp":
                    kp["point"] = new
                else:
                    kp["section"] = new
            elif field == "concept":
                c = next(c for c in d["concepts"] if c["name"] == key)
                if new is None:
                    d["concepts"].remove(c)
                else:
                    c["what_the_source_says"] = new
            elif field == "add_concept":
                d["concepts"].append({"name": key, "what_the_source_says": new})
            log.append(f"- **{field} · {key[:50]}** → {'removed' if new is None else 'corrected'}. {why}")
        d["reviewed"] = True
        d["reviewed_by"] = REVIEWER
        d["review_corrections"] = len(log)
        path.write_text(json.dumps(d, indent=2, ensure_ascii=False))
        rev = ROOT / "data/reviews" / f"{sid}.md"
        text = rev.read_text().split("\n## Human review")[0]
        body = "\n".join(log) if log else "- No corrections needed; every statement matched the note."
        rev.write_text(text.rstrip() + f"\n\n## Human review\n\n{REVIEWER}.\n\n{body}\n")
        print(f"{sid}: {len(log)} corrections")


if __name__ == "__main__":
    main()
