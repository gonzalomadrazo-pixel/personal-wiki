# Ask-mode test test2-paraphrased: answerable, phrased differently from the source

**Question:** Does taking on riskier investments guarantee a bigger payoff, according to Howard Marks?

| | |
|---|---|
| Mode | `ask` (standalone, no chat history) |
| Execution | local: Ollama 0.34.4 on this Mac |
| Network at run time | offline (no internet connection) |
| Model | `gemma4:e2b-it-qat` (gemma4, 4.6B, Q4_0, digest 07ea59a47401) |
| Embeddings | `nomic-embed-text` (F16) |
| Run at | 2026-09-29T21:26:00 |
| Response time | 9.8 s total (1529 prompt tokens, 107 output tokens, 30.2 tok/s) |
| Model memory (Ollama) | gemma4:e2b-it-qat: 3.59 GB, nomic-embed-text:latest: 0.37 GB |

## Expected (written before running)

- **Behaviour:** Says no: riskier assets must offer higher expected or promised returns to attract capital, but those returns aren't guaranteed, and the range of outcomes (including loss) widens as risk rises. Cites the Marks 2006 risk memo.
- **Expected sources:** `marks-2006-risk-memo`
- **Expected evidence:** raw/marks-2006-risk-memo.md › 'Why risk matters, and the misread risk-return line' (PDF pp. 334-336). The source says 'higher returns', 'expected' and 'promised'; the question says 'guarantee' and 'bigger payoff'.

## Retrieved passages

**[S1]** `vault/raw/marks-2006-risk-memo.md` › Why risk matters, and the misread risk-return line, PDF pp. 334-336 (bm25 12.765, cosine 0.763) **(cited)**

> - Capital-market theory: because people dislike risk, riskier investments must offer higher returns to attract money. Returns should be judged relative to the risk taken (risk-adjusted returns).
> - The usual chart shows a line rising from low risk/low return to high risk/high return. Marks objects to the popular reading, "take more risk to make more money." If riskier investments reliably produced higher returns, they would not be riskier.
> - The correct version: riskier investments must offer higher *expected* or *promised* returns, but nothing guarantees those returns will arrive.
> - His redrawn chart shows, at each risk level, a range of possible outcomes that widens as risk rises. Higher risk brings a higher expected return, a chance of lower returns, and sometimes a chance of loss.

**[S2]** `vault/raw/marks-2003-most-important-thing.md` › The limits of macro forecasting; cycles; contrarianism, PDF pp. 229-231 (bm25 2.826, cosine 0.719)

> - Every investor must decide whether they belong to the "I know" school or the "I don't know" school. If you believe you can see the future, you concentrate and time the market. If not, you invest defensively and diversify. Marks is firmly in the second camp: survival comes first.
> - Cycles are inevitable. Prices swing more than fundamentals, and extrapolating trends is one of the most dangerous things an investor can do.
> - Contrarian behaviour works most reliably: only unpopular assets can be truly cheap. Distressed debt profits partly because no one loves a distressed company.
> - Patient opportunism: Oaktree waits for sellers to call rather than chasing a buy list ("our investments find us"), and invests bottom-up.

**[S3]** `vault/raw/marks-2003-most-important-thing.md` › Running an investment firm, PDF pp. 231-233 (bm25 3.077, cosine 0.689)

> - Say what you will do, and then do it. Stay inside the client's mandate.
> - Keep flexibility on tactics while being specific about philosophy, goals and style.
> - Refuse to manage too much money. Good performance brings more assets, and too many assets eventually hurt performance. Oaktree has capped its strategies and turned money away for twenty years.

**[S4]** `vault/raw/marks-2003-most-important-thing.md` › Price and value come first, PDF pp. 226-227 (bm25 3.744, cosine 0.652)

> - Above all, the relationship between price and value matters. No asset is so good it can't be a bad investment at too high a price, and few are so bad they can't be good investments if cheap enough.
> - No asset class has a birthright to high returns. You'd ask the price before buying someone's car, so buying an investment without judging its price is just as silly. Examples: tech stocks in the late 1990s (bought at any price) and junk bonds in the 1970s-80s (avoided at any price).
> - The biggest losses he has seen came from buying "perfect" companies at prices that assumed perfection. A good company is not the same as a good investment.
> - He wants the best *buys*, not the best companies.

**[S5]** `vault/raw/marks-2006-risk-memo.md` › Bearing risk intelligently for profit, PDF pp. 343-345 (bm25 2.896, cosine 0.679)

> - Keynes: a speculator knowingly runs risks; an investor runs risks without knowing it. Unknowingly bearing risk in popular, "can't-lose" assets is the big mistake. Knowingly accepting recognised risk at the right price is behind many of the best investments.
> - Life-insurance analogy (his answer to a reporter about junk bonds): insurers know everyone will die, yet they are conservative businesses. The risk is known, can be analysed, can be diversified and is well paid for. Oaktree tries to do the same with high-yield bonds.
> - Risky assets can be good investments if they are cheap enough; the skill is knowing when.
> - Risk control is not risk avoidance. Avoiding all risk also means avoiding returns above the risk-free rate. The aim is "risk intelligence": understanding, managing and being paid for the risks you take.

**[S6]** `vault/raw/buffett-1993-letter.md` › Concentration instead of diversification, PDF p. 405 (bm25 3.583, cosine 0.648)

> - Buffett and Munger decided long ago that it is too hard to make hundreds of smart decisions in a lifetime. Their strategy requires being smart only a few times; he says they will now settle for one good idea a year.
> - Many experts would call this concentrated strategy riskier. Buffett disagrees. Concentration can *reduce* risk if it makes the investor think harder about a business and demand more comfort with its economics before buying.
> - He defines risk using the dictionary: the possibility of loss or injury.

## Actual Gemma answer

```text
No, taking on riskier investments does not guarantee a bigger payoff according to Howard Marks. Marks states that riskier investments must offer higher *expected* or *promised* returns, but nothing guarantees those returns will materialize [S1]. He also notes that higher risk brings a higher expected return, a chance of lower returns, and sometimes a chance of loss [S1]. The correct view is that riskier investments must offer higher expected or promised returns, but the passage does not state that these returns are guaranteed [S1].
```

## Automated checks

- Expected source retrieved: `marks-2006-risk-memo` at rank 1
- Citation check: **answered**; cited [S1]
- Sources cited: `marks-2006-risk-memo`

## Assessment (human)

**Verdict: PASS, with two small flaws.**

- **Retrieval:** the expected passage (`marks-2006-risk-memo.md` › "Why risk matters, and the misread risk-return line", PDF pp. 334-336) was ranked 1st, with the highest keyword score (12.8) and highest similarity (0.76). The question's wording ("guarantee a bigger payoff") differs from the note's ("higher *expected* or *promised* returns… nothing guarantees them"). Retrieval still worked, partly because both share the words "riskier investments".
- **Answer vs. evidence:** correct. It says no, riskier investments must *offer* higher expected returns but they aren't guaranteed, and that higher risk widens the outcomes, including loss. All of this is in [S1].
- **Flaws:**
  1. The opening sentence ("No, taking on riskier investments does not guarantee…") has no citation; the harness flagged it as an uncited sentence. Its content is supported by [S1].
  2. The last sentence repeats the second.
- **History:** in dry run 2 this test wrongly began with "INSUFFICIENT EVIDENCE". The rule rewrite in `wiki-instructions.md` fixed that, and the fix held offline.

_Assessment written by checking each cited passage against `vault/raw/` (drafted with AI assistance)._
