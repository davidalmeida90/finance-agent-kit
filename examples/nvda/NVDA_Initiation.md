# NVIDIA Corporation (NASDAQ: NVDA)

**Initiation of coverage | 4 September 2026 | Price $231.71 | Market cap $5.68tn**

Base period is the twelve months ended 26 July 2026, built from the Q2 FY2027 10-Q (accession 0001045810-26-000075, filed 26 August 2026) plus the three preceding quarters.

---

## Conclusion

Valuation does not resolve to a single number, and that spread is the finding rather than a failure of the exercise.

| Method | Implied value per share | Versus $231.71 |
|---|---|---|
| DCF, Gordon growth terminal | $117.07 | -49.5% |
| DCF, 18x exit EBITDA terminal | $260.00 | +12.2% |
| Bear case, Gordon | $78.09 | -66.3% |
| Bull case, Gordon | $157.52 | -32.0% |
| Bull case, exit multiple | $360.62 | +55.6% |

Two terminal methods applied to an identical cash flow schedule produce $117 and $260. Any report quoting one of those as a price target while holding the other in reserve is presenting a choice as a calculation.

## What actually drives the answer

Discount rate, not growth.

NVIDIA's observed five year beta is 2.217. Applying CAPM with a 4.772% risk free rate and a 5.5% equity risk premium gives a cost of equity of 16.97%, and since the company carries net cash, WACC is effectively the same 16.97%. At that rate a Gordon terminal value cannot support the market price under any growth path tested, including a bull case that takes revenue from $303bn to $1.30tn by FY2031.

Reversing the calculation is more informative than the forecast. Holding the base case cash flows fixed, the discount rate that reproduces the current $231.71 price is **10.17%**, which implies a beta near **0.98**.

So the market is not disagreeing about NVIDIA's growth. Base case revenue growth of 55% falling to 10% over five years is already aggressive, and it still leaves the shares 49.5% overvalued at the observed beta. Market pricing instead implies NVIDIA carries roughly market average systematic risk. Reconciling a 2.2 realised beta with a 1.0 priced beta is the analytical question this name turns on.

## Sensitivity, base case, Gordon growth

Implied price per share.

| WACC \ terminal g | 2.0% | 2.5% | 3.0% | 3.5% | 4.0% |
|---|---|---|---|---|---|
| 15.0% | 130 | 133 | 137 | 141 | 146 |
| 16.0% | 120 | 123 | 126 | 130 | 134 |
| **17.0%** | 112 | 114 | **117** | 120 | 123 |
| 18.0% | 105 | 107 | 109 | 111 | 114 |
| 19.0% | 98 | 100 | 102 | 104 | 106 |

Across the entire grid the range is $98 to $146. Moving terminal growth by a full 200 basis points shifts value by roughly 12%, while moving WACC by the same amount shifts it by roughly 30%. Terminal value represents 58.7% of enterprise value in the base case, which is normal for a growth asset and is the reason the discount rate dominates.

## Operating performance

| | FY2023 | FY2024 | FY2025 | FY2026 | TTM Q2-FY27 |
|---|---|---|---|---|---|
| Revenue ($m) | 26,974 | 60,922 | 130,497 | 215,938 | 302,948 |
| Growth | | +125.8% | +114.2% | +65.5% | |
| Gross margin | 56.9% | 72.7% | 75.0% | 71.1% | 74.7% |
| Operating margin | 15.7% | 54.1% | 62.4% | 60.4% | 65.2% |
| Capex ($m) | 1,833 | 1,069 | 3,236 | 6,042 | 6,680 |

Three points carry the model.

Growth is decelerating in percentage terms while accelerating in absolute dollars. FY2026 added $85bn of revenue on a 65.5% growth rate, and the trailing twelve months added a further $87bn.

Margins are still expanding at scale, which is unusual. Operating margin reached 65.2% on the trailing twelve months, above the 60.4% posted in FY2026, so operating leverage has not yet exhausted itself.

Capital intensity is minimal. Capex ran at 2.2% of revenue, a consequence of the fabless model, which is why free cash flow conversion is high and why NOPAT dominates the cash flow build. Working capital is the real drag, since receivables reached $38.5bn and inventory $21.4bn at FY2026 year end.

## Comparable companies

| | Gross margin | Operating margin | EV/EBITDA |
|---|---|---|---|
| NVDA | 74.7% | 66.2% | 27.2x |
| INTC | 38.9% | 12.2% | 29.6x |
| QCOM | 54.2% | 18.5% | 15.3x |
| MU | 72.6% | 80.4% | 15.6x |
| Peer median, excluding NVDA | 54.2% | 18.5% | 15.6x |

Comps are the weakest part of this analysis and should be read as indicative only. Sample of three peers sits well below the five to ten range the methodology calls for. TSM was excluded because it reports in TWD and would distort every multiple. AMD and AVGO returned incomplete data from the free feed and were dropped rather than estimated. MU's 80.4% operating margin reflects a memory cycle peak rather than a normalised level, and INTC's 29.6x EV/EBITDA reflects a depressed earnings base rather than a growth premium. Both distort a three name median.

NVIDIA trades at 27.2x EV/EBITDA against a 15.6x peer median, a 74% premium, while earning 3.6x the peer median operating margin. Premium is large in absolute terms and defensible against that margin gap, but a three company median carrying two distorted observations cannot carry the weight of a valuation conclusion.

Note on the model: the 18x exit multiple used in the DCF terminal value sits above this 15.6x peer median. That assumption is therefore a judgement that NVIDIA deserves a premium exit, not a peer derived figure, and it is worth $143 per share against the Gordon alternative.

## Risks

Discount rate risk dominates. A 200 basis point move in WACC moves value by roughly 30%, and the beta input is itself unstable because it is estimated over a period of extreme price appreciation.

Terminal method risk is second. Choice between Gordon growth and an exit multiple is worth $143 per share on identical cash flows.

Concentration and cyclicality are not modelled here. A five year horizon with smooth deceleration implicitly assumes no order air pocket, which the semiconductor cycle has historically not delivered.

## What this analysis does not establish

- Net debt uses FY2026 year end balances. Cash has almost certainly risen given $102.7bn of FY2026 operating cash flow, so net cash is understated. Effect is immaterial against a $5.68tn market capitalisation.
- Share count uses FY2026 weighted average diluted shares of 24,514m. Buybacks totalled $40.1bn in FY2026 and continue, so the current count is likely lower and value per share correspondingly understated.
- Segment detail, customer concentration and geographic exposure were not extracted. No revenue build by product line was attempted.
- Peer set is incomplete, as noted above.
- Terminal exit multiple of 18x is an assumption informed by a four company median, not a defensible peer derived figure.

## Sources

Filed financials: SEC XBRL retrieved through the `sec-edgar` MCP. FY2023 to FY2026 from the FY2026 10-K, trailing twelve months from the Q2 FY2027 10-Q (accession 0001045810-26-000075) plus three prior quarters.

Market data: prices, market capitalisation, beta, peer multiples and the 10 year Treasury yield retrieved 4 September 2026. Market data is not filed data and has not been independently verified.

Model: `output/NVDA_DCF_Model.xlsx`, 148 live formulas, validated with zero formula errors.
