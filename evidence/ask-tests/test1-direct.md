# Ask-mode test test1-direct: direct question answered by one source

**Question:** What is Giverny Capital's Rule of Three?

| | |
|---|---|
| Mode | `ask` (standalone, no chat history) |
| Execution | local: Ollama 0.34.4 on this Mac |
| Network at run time | offline (no internet connection) |
| Model | `gemma4:e2b-it-qat` (gemma4, 4.6B, Q4_0, digest 07ea59a47401) |
| Embeddings | `nomic-embed-text` (F16) |
| Run at | 2026-09-29T21:25:49 |
| Response time | 9.78 s total (1664 prompt tokens, 119 output tokens, 30.4 tok/s) |
| Model memory (Ollama) | gemma4:e2b-it-qat: 3.59 GB, nomic-embed-text:latest: 0.37 GB |

## Expected (written before running)

- **Behaviour:** Lists the three parts of the rule, cites the Giverny 2002 letter, and ideally notes that the rule is empirical and meant to help investors stay rational.
- **Expected sources:** `rochon-2002-giverny-letter`
- **Expected evidence:** raw/rochon-2002-giverny-letter.md › 'The Rule of Three' (PDF p. 15): one year in three the market falls more than 10%; one stock in three disappoints; one year in three the portfolio lags the indexes.

## Retrieved passages

**[S1]** `vault/raw/rochon-2002-giverny-letter.md` › The Rule of Three, PDF p. 15 (bm25 9.036, cosine 0.723) **(cited)**

> - Rochon's **Rule of Three** lists three market realities to accept in advance:
>   1. one year out of three, the stock market will fall by more than 10%;
>   2. one stock out of three that he buys will disappoint;
>   3. one year out of three, the portfolio will underperform the indexes.
> - He calls it an observed, not scientific, rule. Its value is psychological: accepting bad years and stock mistakes beforehand helps you act rationally when they happen.
> - The pattern is not regular. Bad years can bunch together. Sequoia Fund lagged the S&P 500 in its first four years (1970-73) before becoming a top performer. Keynes' Chest Fund lost more than the British market in its first three years, yet over 18 years earned about 9% a year versus about -1% for the market, while trailing in roughly one year out of three.
> - Because the sequence can't be predicted, the best strategy is to stay invested and keep improving stock selection. He calls corrections "partners," since they create opportunities.

**[S2]** `vault/raw/rochon-2002-giverny-letter.md` › Mistakes of the year: "Mistake du jour", PDF pp. 21-23 (bm25 3.334, cosine 0.637)

> - **Bronze — Heartland Express:** a low-cost trucker with a founder-CEO owning 40%, a modest salary and no options. He sold in 1999 when growth paused; the stock tripled. The error was impatience.
> - **Silver — Expedia:** he recommended it at $10 but hesitated to buy for all accounts, and waited in vain for the price to fall back. It later traded around $65. His lesson: discipline is following your rules; wisdom is knowing when to break them.
> - **Gold — Richelieu Hardware:** a high-return, fast-growing distributor recommended by his partner Bernard Mooney. He waited years, bought too little and wouldn't pay a bit more. The stock rose about fivefold in five years — even though the lock on his own front door was made by Richelieu.

**[S3]** `vault/raw/buffett-1987-letter.md` › When to sell, and the three permanent holdings, PDF pp. 232-233 (bm25 5.018, cosine 0.587)

> - Berkshire sells when the market clearly overvalues a business, or when it needs money for something more undervalued or better understood. It does not sell just because a stock has risen or has been held a long time.
> - Three stocks — Capital Cities/ABC, GEICO and The Washington Post — are treated as permanent holdings, like wholly owned subsidiaries. He would not sell them even if they became overpriced (except, if absolutely necessary, to pay extraordinary insurance losses).
> - He prefers a wonderful business at a sensible price to a mediocre business at a bargain price. He jokes that it took him about 20 years to learn this, during which his "bargains" included a farm-equipment maker, a department store and a textile mill.

**[S4]** `vault/raw/rochon-2002-giverny-letter.md` › Owner's earnings as the scorecard, PDF pp. 20-21 (bm25 2.448, cosine 0.658)

> - Giverny measures itself by the growth in its companies' earnings and long-term prospects, not by short-term stock prices. This follows Buffett's look-through earnings idea.
> - In 2002 the portfolio's stock prices were roughly flat, but its owner's earnings rose about 18-20%, with an ROE of about 18%. Over about five years, prices tend to reflect earnings growth.
> - Gaps between price and business progress (Bed Bath & Beyond's EPS +40% with the stock +3%) are opportunities.

**[S5]** `vault/raw/rochon-2002-giverny-letter.md` › The gardener and the investor, PDF pp. 23-24 (bm25 2.397, cosine 0.673)

> - Echoing Munger's advice to use many mental models, Rochon compares investing to Monet's garden at Giverny. Know your soil and climate (some sectors he can't understand). Tend the garden continuously. Don't pull the flowers to water the weeds, as Peter Lynch warned — that is, don't sell winners to buy more losers.
> - Time and patience matter most. Great companies, like trees, take decades to grow. He likes long-tenured, founder-led companies such as Fastenal, Cognex, Bed Bath & Beyond and Costco.

**[S6]** `vault/raw/buffett-1987-letter.md` › Controlled companies vs. marketable stocks; capital allocation, PDF pp. 233-235 (bm25 3.254, cosine 0.62)

> - Owning a controlled company has two advantages: Berkshire gets to allocate its capital, and it has tax advantages at 80%+ ownership.
> - Many CEOs reach the top through marketing, production or administration and are not skilled at capital allocation. Yet after ten years, a CEO whose company retains 10% of net worth a year has deployed more than 60% of all its capital.
> - The stock market sometimes compensates by offering pieces of great businesses at far below negotiated-deal prices. Examples: Washington Post shares bought in 1973 and GEICO shares bought in 1976-80 at prices below their 1987 annual per-share earnings.
> - Accounting quirk: GAAP shows the market value of these minority stakes on the balance sheet, but only their small dividends in income. Buffett ignores GAAP and focuses on future earning power.

## Actual Gemma answer

```text
Giverny Capital's Rule of Three lists three market realities to accept in advance [S1]. These realities are: one year out of three, the stock market will fall by more than 10% [S1], one stock out of three that is purchased will disappoint [S1], and one year out of three, the portfolio will underperform the indexes [S1]. This rule is described as an observed, rather than scientific, rule, and its value is psychological, as accepting bad years and stock mistakes beforehand helps one act rationally when they occur [S1].
```

## Automated checks

- Expected source retrieved: `rochon-2002-giverny-letter` at rank 1
- Citation check: **answered**; cited [S1]
- Sources cited: `rochon-2002-giverny-letter`

## Assessment (human)

**Verdict: PASS.**

- **Retrieval:** the expected passage (`rochon-2002-giverny-letter.md` › The Rule of Three, PDF p. 15) was ranked 1st, by both keyword score (BM25 9.0, the highest) and embedding similarity (0.72).
- **Answer vs. evidence:** I checked every claim against [S1]:
  - all three parts of the rule are correct (market falls >10% one year in three; one stock in three disappoints; the portfolio lags the indexes one year in three);
  - "observed, not scientific" and the psychological purpose both appear in the passage.
- **Citations:** every sentence cites [S1], and [S1] supports each one. No outside knowledge was added.
- **Minor:** the answer is a close paraphrase of the passage, which is expected for a direct question.

_Assessment written by checking each cited passage against `vault/raw/` (drafted with AI assistance)._
