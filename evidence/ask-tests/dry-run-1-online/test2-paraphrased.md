# Ask-mode test test2-paraphrased: answerable, phrased differently from the source

**Question:** Does taking on riskier investments guarantee a bigger payoff, according to Howard Marks?

| | |
|---|---|
| Mode | `ask` (standalone, no chat history) |
| Execution | local: Ollama 0.34.4 on this Mac |
| Network at run time | online (internet reachable) |
| Model | `gemma4:e2b-it-qat` (gemma4, 4.6B, Q4_0, digest 07ea59a47401) |
| Embeddings | `nomic-embed-text` (F16) |
| Run at | 2026-09-29T13:21:34 |
| Response time | 7.65 s total (1175 prompt tokens, 68 output tokens, 26.3 tok/s) |
| Model memory (Ollama) | gemma4:e2b-it-qat: 1.66 GB, nomic-embed-text:latest: 0.37 GB |

## Expected (written before running)

- **Behaviour:** Says no: riskier assets must offer higher expected or promised returns to attract capital, but those returns aren't guaranteed, and the range of outcomes (including loss) widens as risk rises. Cites the Marks 2006 risk memo.
- **Expected sources:** `marks-2006-risk-memo`
- **Expected evidence:** raw/marks-2006-risk-memo.md › 'Why risk matters, and the misread risk-return line' (PDF pp. 334-336). The source says 'higher returns', 'expected' and 'promised'; the question says 'guarantee' and 'bigger payoff'.

## Retrieved passages

**[S1]** `vault/raw/marks-2006-risk-memo.md` › Why risk matters, and the misread risk-return line, PDF pp. 334-336 (bm25 12.78, cosine 0.763) **(cited)**

> - Capital-market theory: because people dislike risk, riskier investments must offer higher returns to attract money. Returns should be judged relative to the risk taken (risk-adjusted returns).
> - The usual chart shows a line rising from low risk/low return to high risk/high return. Marks objects to the popular reading, "take more risk to make more money." If riskier investments reliably produced higher returns, they would not be riskier.
> - The correct version: riskier investments must offer higher *expected* or *promised* returns, but nothing guarantees those returns will arrive.
> - His redrawn chart shows, at each risk level, a range of possible outcomes that widens as risk rises. Higher risk brings a higher expected return, a chance of lower returns, and sometimes a chance of loss.

**[S2]** `vault/raw/marks-2006-risk-memo.md` › Overview (bm25 4.866, cosine 0.66)

> These are my notes on Howard Marks' January 2006 memo devoted entirely to risk. A Deloitte article on corporate risk, read for a board meeting, prompted it.

**[S3]** `vault/raw/marks-2003-most-important-thing.md` › The limits of macro forecasting; cycles; contrarianism, PDF pp. 229-231 (bm25 2.837, cosine 0.719)

> - Every investor must decide whether they belong to the "I know" school or the "I don't know" school. If you believe you can see the future, you concentrate and time the market. If not, you invest defensively and diversify. Marks is firmly in the second camp: survival comes first.
> - Cycles are inevitable. Prices swing more than fundamentals, and extrapolating trends is one of the most dangerous things an investor can do.
> - Contrarian behaviour works most reliably: only unpopular assets can be truly cheap. Distressed debt profits partly because no one loves a distressed company.
> - Patient opportunism: Oaktree waits for sellers to call rather than chasing a buy list ("our investments find us"), and invests bottom-up.

**[S4]** `vault/raw/marks-2003-most-important-thing.md` › Running an investment firm, PDF pp. 231-233 (bm25 3.103, cosine 0.689)

> - Say what you will do, and then do it. Stay inside the client's mandate.
> - Keep flexibility on tactics while being specific about philosophy, goals and style.
> - Refuse to manage too much money. Good performance brings more assets, and too many assets eventually hurt performance. Oaktree has capped its strategies and turned money away for twenty years.

**[S5]** `vault/raw/marks-2006-risk-memo.md` › Bearing risk intelligently for profit, PDF pp. 343-345 (bm25 2.869, cosine 0.679)

> - Keynes: a speculator knowingly runs risks; an investor runs risks without knowing it. Unknowingly bearing risk in popular, "can't-lose" assets is the big mistake. Knowingly accepting recognised risk at the right price is behind many of the best investments.
> - Life-insurance analogy (his answer to a reporter about junk bonds): insurers know everyone will die, yet they are conservative businesses. The risk is known, can be analysed, can be diversified and is well paid for. Oaktree tries to do the same with high-yield bonds.
> - Risky assets can be good investments if they are cheap enough; the skill is knowing when.
> - Risk control is not risk avoidance. Avoiding all risk also means avoiding returns above the risk-free rate. The aim is "risk intelligence": understanding, managing and being paid for the risks you take.

## Actual Gemma answer

```text
Taking on riskier investments does not guarantee a bigger payoff [S1]. Capital-market theory suggests that riskier investments must offer higher expected or promised returns, but nothing guarantees those returns will materialize [S1]. Higher risk brings a higher expected return, a chance of lower returns, and sometimes a chance of loss [S1].
```

## Automated checks

- Expected source retrieved: `marks-2006-risk-memo` at rank 1
- Citation check: **answered**; cited [S1]
- Sources cited: `marks-2006-risk-memo`

## Assessment (human)

_To be written after opening the cited passages: does each material claim follow from them?_
