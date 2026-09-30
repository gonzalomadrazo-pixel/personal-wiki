# Ask-mode test test3-two-sources: connects two sources

**Question:** How do Warren Buffett and Howard Marks each define investment risk, and do they agree that volatility is the right measure?

| | |
|---|---|
| Mode | `ask` (standalone, no chat history) |
| Execution | local: Ollama 0.34.4 on this Mac |
| Network at run time | online (internet reachable) |
| Model | `gemma4:e2b-it-qat` (gemma4, 4.6B, Q4_0, digest 07ea59a47401) |
| Embeddings | `nomic-embed-text` (F16) |
| Run at | 2026-09-29T13:21:45 |
| Response time | 10.19 s total (1193 prompt tokens, 167 output tokens, 28.2 tok/s) |
| Model memory (Ollama) | gemma4:e2b-it-qat: 1.66 GB, nomic-embed-text:latest: 0.37 GB |

## Expected (written before running)

- **Behaviour:** Buffett: risk is the possibility of loss or injury, and not keeping purchasing power plus modest interest over the holding period; beta and volatility are the wrong measure. Marks: risk is first of all the likelihood of losing money; volatility was chosen for convenience. Both reject volatility. Cites both sources.
- **Expected sources:** `buffett-1993-letter`, `marks-2006-risk-memo`
- **Expected evidence:** raw/buffett-1993-letter.md › 'Concentration instead of diversification', 'Why beta and volatility are the wrong measure of risk' and 'Buffett's definition of real investment risk' (PDF pp. 405-406); raw/marks-2006-risk-memo.md › 'Why volatility is not risk' and 'What risk really is' (PDF pp. 336-338).

## Retrieved passages

**[S1]** `vault/raw/buffett-1993-letter.md` › Why beta and volatility are the wrong measure of risk, PDF pp. 405-406 (bm25 12.736, cosine 0.788) **(cited)**

> - Academics define risk as a stock's volatility relative to the market (beta), calculated precisely from past prices. Buffett says this forgets that it is better to be approximately right than precisely wrong.
> - For business owners this definition is absurd. Under beta theory, the Washington Post stock became "riskier" after it fell sharply in 1973. But the lower price made it a better deal, not a riskier one.
> - True investors welcome volatility (Graham's Mr. Market again). Wild price swings mean solid businesses sometimes sell at irrationally low prices, and an investor free to ignore or exploit the market is not harmed by that.
> - A beta purist studies only price history and ignores what the company makes, its competitors and its debt. Buffett prefers the opposite and would not mind if markets closed for a year or two after he bought.

**[S2]** `vault/raw/marks-2006-risk-memo.md` › Why volatility is not risk, PDF pp. 336-337 (bm25 9.958, cosine 0.772) **(cited)**

> - Academics chose volatility as the measure of risk mostly for convenience. It is objective, historical and easy to put in a formula.
> - Marks has never met an investor who refused a deal because the price might fluctuate or have a down quarter. So volatility is probably not what the market prices.
> - Practical flaws: a stock drifting from 50 to 80 and one falling from 50 to 20 can show the same volatility. A stock that rose smoothly to 80 and then dropped to 50 is called riskier at 50 than it was at 80. And historic volatility assumes the future will look like the past.

**[S3]** `vault/raw/buffett-1993-letter.md` › Overview (bm25 6.428, cosine 0.777)

> These are my notes on the common-stock section of Buffett's letter for 1993, which includes his best-known argument against defining risk as volatility.

**[S4]** `vault/raw/marks-2006-risk-memo.md` › Risk depends on the investor, PDF p. 341 (bm25 7.397, cosine 0.714) **(cited)**

> - Is concentration risky? Only for someone who cannot see the future clearly. Diversification is a trade of return for safety, made because our knowledge is imperfect.
> - Is illiquidity risky? Buffett and Munger hold huge, hard-to-sell positions and whole companies without trouble, because they know what they are doing and won't face forced selling.
> - Are distressed-debt funds risky? The holdings are messy, but the funds buy very cheaply, have skilled teams and a strong record. The answer depends on how you define risk. No single number captures risk, and few assets are risky or safe in themselves.

**[S5]** `vault/raw/buffett-1993-letter.md` › Buffett's definition of real investment risk, PDF p. 406 (bm25 4.638, cosine 0.764) **(cited)**

> - The real risk: whether the investor's total after-tax receipts over the holding period (including the sale proceeds) will give at least the purchasing power they started with, plus modest interest.
> - Five factors bear on that risk:
>   1. how certainly the business's long-term economics can be evaluated;
>   2. how certainly management can be evaluated, both on realising the business's potential and on using cash flows wisely;
>   3. how certainly management will pass the rewards to shareholders rather than to itself;
>   4. the purchase price;
>   5. the taxes and inflation that will reduce the investor's real return.
> - These factors are fuzzy and cannot be pulled from a database, but they can often be judged well enough to be useful.

## Actual Gemma answer

```text
Warren Buffett defines real investment risk as whether the investor's total after-tax receipts over the holding period, including sale proceeds, will yield at least the original purchasing power plus modest interest [S5]. He suggests that true investors welcome volatility because wild price swings allow solid businesses to sometimes sell at irrationally low prices, and an investor free to ignore or exploit the market is not harmed by that [S1]. Howard Marks argues that volatility is not the measure of risk because academics chose it for convenience, and practical flaws exist, such as a stock drifting from 50 to 80 and then falling from 50 to 20 showing the same volatility [S2]. Marks also states that risk depends on the investor, and diversification is a trade of return for safety because knowledge is imperfect [S4].
```

## Automated checks

- Expected source retrieved: `buffett-1993-letter` at rank 1; `marks-2006-risk-memo` at rank 2
- Citation check: **answered**; cited [S1], [S2], [S4], [S5]
- Sources cited: `buffett-1993-letter`, `marks-2006-risk-memo`

## Assessment (human)

_To be written after opening the cited passages: does each material claim follow from them?_
